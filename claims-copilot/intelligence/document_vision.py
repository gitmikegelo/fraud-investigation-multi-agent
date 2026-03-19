"""
Vision-based document analysis using Claude Haiku 4.5 via AWS Bedrock.

Sends claim document images to Haiku 4.5 for visual inspection against
the 13 DOC checks. Falls back to metadata-based checks when no image is available.
"""

import os
import re
import json
import glob
import base64
import io
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image

from .document_analysis import DocCheckResult

load_dotenv()

logger = logging.getLogger(__name__)

# Bedrock config
_REGION = os.getenv("AWS_REGION", "us-east-1")
_VISION_MODEL = os.getenv(
    "BEDROCK_VISION_MODEL_ID",
    os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
)

# Images root — workspace-level images/ folder
_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"

# Supported image extensions
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
_MEDIA_TYPES = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".gif": "gif",
    ".webp": "webp",
}

# ── Vision prompt ────────────────────────────────────────────────────────────

_VISION_PROMPT = """\
You are a medical document forensics analyst for a supplemental health insurance company.
Examine this document image and evaluate it against ALL 13 checks below.
For EACH check, provide a JSON object with your finding.

THE 13 DOCUMENT CHECKS:

DOC-001  Font Inconsistency — Are there multiple font styles/families within the same document?
DOC-002  Erasure Indicators — Is there any evidence of erased, whited-out, or overwritten content?
DOC-003  Typed Over Handwritten — Is there typed text overlaying handwritten dates, notes, or entries?
DOC-004  Entirely Handwritten — Is this an entirely handwritten report (unusual for a modern medical facility)?
DOC-005  Missing Standard Headers — Does the document lack standard medical record headers (facility name, OVN, HCF identifiers)?
DOC-006  Black & White Copy — Is this a black-and-white photocopy that could mask alterations?
DOC-007  Editable Format — Does this appear to be from an editable document (Word/template) rather than a proper medical record system?
DOC-008  Inconsistent Font Sizes — Are there inconsistent font sizes within what should be a uniformly formatted document?
DOC-009  Medical Terminology Errors — Are there misspelled medical terms, incorrect procedure names, or non-standard medical language?
DOC-010  Missing Vitals/Medications — For a full medical record, are vitals or medication lists absent?
DOC-011  Signature Anomaly — Does the provider signature look stamped, photocopied, or inconsistent with a genuine signature?
DOC-012  Email Submission Format — Does the document appear to have been submitted via email (email headers, forwarding artifacts) rather than through a secure portal?
DOC-013  Non-Requesting Provider — Do any elements suggest this record is from a different provider than the one who requested/submitted the claim?

RESPOND WITH ONLY valid JSON — no markdown fences, no commentary outside the JSON.
Use this exact structure:

{
  "checks": [
    {
      "check_id": "DOC-001",
      "check_name": "Font Inconsistency",
      "passed": true,
      "severity": "INFO",
      "explanation": "Single consistent font throughout the document."
    }
  ],
  "overall_assessment": "Brief 1-2 sentence summary of document authenticity.",
  "confidence": 0.92
}

Severity values: "CRITICAL" for high-risk failures, "WARNING" for medium, "INFO" for low/pass.
Set passed=true if the check finds NO issues, passed=false if an issue IS detected.
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _claim_id_to_image_key(claim_id: str) -> str:
    """Convert claim ID like 'WC-247' → 'wc247' for image file lookup."""
    return re.sub(r"[^a-z0-9]", "", claim_id.lower())


def find_claim_images(claim_id: str, images_dir: Optional[Path] = None) -> List[Path]:
    """Find all image files in the images directory matching a claim ID."""
    root = images_dir or _IMAGES_DIR
    if not root.exists():
        return []

    key = _claim_id_to_image_key(claim_id)
    matches = []
    for ext in _IMAGE_EXTENSIONS:
        # Exact match: wc247.png
        exact = root / f"{key}{ext}"
        if exact.exists():
            matches.append(exact)
        # Numbered variants: wc247_1.png, wc247_2.png
        for p in sorted(root.glob(f"{key}_*{ext}")):
            matches.append(p)
    return matches


def _load_image(path: Path, max_bytes: int = 4_800_000) -> Tuple[bytes, str]:
    """Read image bytes, resize/compress if over max_bytes (Bedrock limit is 5 MB)."""
    ext = path.suffix.lower()
    media = _MEDIA_TYPES.get(ext, "png")
    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) <= max_bytes:
        return raw, media

    # Resize to fit under the limit
    logger.info("Image %s is %d bytes, compressing to fit Bedrock 5 MB limit", path.name, len(raw))
    img = Image.open(io.BytesIO(raw))

    # Progressive downscale until under limit
    quality = 85
    scale = 1.0
    for _ in range(10):
        scale *= 0.8
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        save_fmt = "PNG" if media == "png" else "JPEG"
        if save_fmt == "JPEG":
            resized.save(buf, format=save_fmt, quality=quality, optimize=True)
        else:
            resized.save(buf, format=save_fmt, optimize=True)
        compressed = buf.getvalue()
        if len(compressed) <= max_bytes:
            logger.info("Compressed to %d bytes (%dx%d)", len(compressed), new_size[0], new_size[1])
            out_media = "jpeg" if save_fmt == "JPEG" else media
            return compressed, out_media
        quality = max(quality - 10, 40)

    # Last resort: convert to JPEG at low quality
    buf = io.BytesIO()
    resized = img.resize((int(img.width * 0.3), int(img.height * 0.3)), Image.LANCZOS)
    if resized.mode in ("RGBA", "P"):
        resized = resized.convert("RGB")
    resized.save(buf, format="JPEG", quality=50, optimize=True)
    return buf.getvalue(), "jpeg"


def _get_bedrock_client():
    """Create a Bedrock Runtime client (reused across calls)."""
    return boto3.client("bedrock-runtime", region_name=_REGION)


# ── Core Vision Analysis ─────────────────────────────────────────────────────

def analyze_document_image(
    image_path: Path,
    bedrock_client=None,
) -> Dict:
    """
    Send a single document image to Claude Haiku 4.5 for the 13-check analysis.

    Returns the parsed JSON response from the model, or an error dict.
    """
    client = bedrock_client or _get_bedrock_client()
    image_bytes, media_type = _load_image(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": media_type,
                        "source": {"bytes": image_bytes},
                    }
                },
                {"text": _VISION_PROMPT},
            ],
        }
    ]

    try:
        response = client.converse(
            modelId=_VISION_MODEL,
            messages=messages,
            inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
        )
        # Extract text from response
        output_text = ""
        for block in response.get("output", {}).get("message", {}).get("content", []):
            if "text" in block:
                output_text += block["text"]

        # Parse JSON from response (strip markdown fences if model wraps them)
        cleaned = re.sub(r"^```(?:json)?\s*", "", output_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse vision model response as JSON: %s", e)
        return {"error": f"JSON parse error: {e}", "raw": output_text}
    except ClientError as e:
        logger.error("Bedrock API error: %s", e)
        return {"error": str(e)}


def _parse_vision_results(vision_response: Dict) -> List[DocCheckResult]:
    """Convert the structured JSON from Haiku 4.5 into DocCheckResult objects."""
    results = []
    checks = vision_response.get("checks", [])
    assessment = vision_response.get("overall_assessment", "")
    confidence = vision_response.get("confidence", 0.0)

    for check in checks:
        results.append(DocCheckResult(
            check_id=check.get("check_id", "UNKNOWN"),
            check_name=check.get("check_name", "Unknown Check"),
            passed=check.get("passed", True),
            explanation=check.get("explanation", ""),
            severity=check.get("severity", "INFO"),
            details={
                "source": "vision_ai",
                "confidence": confidence,
                "overall_assessment": assessment,
            },
        ))

    return results


# ── Public API ───────────────────────────────────────────────────────────────

def run_vision_document_checks(
    claim_id: str,
    images_dir: Optional[Path] = None,
    bedrock_client=None,
) -> Optional[List[DocCheckResult]]:
    """
    Run the 13 DOC checks using Claude Haiku 4.5 vision on the claim's document image(s).

    Returns:
        List[DocCheckResult] if an image was found and analyzed successfully.
        None if no image exists for this claim (caller should fall back to metadata checks).
    """
    images = find_claim_images(claim_id, images_dir)
    if not images:
        return None  # no image → caller uses metadata fallback

    # Use the first image (primary document)
    primary_image = images[0]
    logger.info("Analyzing document image for %s: %s", claim_id, primary_image.name)

    client = bedrock_client or _get_bedrock_client()
    vision_response = analyze_document_image(primary_image, client)

    if "error" in vision_response:
        logger.warning("Vision analysis failed for %s: %s", claim_id, vision_response["error"])
        return None  # fall back to metadata

    results = _parse_vision_results(vision_response)

    # If we got fewer than 13 checks back, the model may have skipped some — log it
    if len(results) < 13:
        logger.warning(
            "Vision returned %d/13 checks for %s — some may be missing",
            len(results), claim_id,
        )

    # If multiple images exist, analyze additional ones and merge notable findings
    if len(images) > 1:
        for extra_image in images[1:]:
            extra_response = analyze_document_image(extra_image, client)
            if "error" not in extra_response:
                extra_results = _parse_vision_results(extra_response)
                # Merge: if additional image flags something the primary didn't, add it
                primary_ids = {r.check_id for r in results}
                failed_extras = [r for r in extra_results if not r.passed and r.check_id in primary_ids]
                for er in failed_extras:
                    # Override the primary result if this image flagged it
                    for i, pr in enumerate(results):
                        if pr.check_id == er.check_id and pr.passed:
                            er.details["source_image"] = extra_image.name
                            results[i] = er
                            break

    return results
