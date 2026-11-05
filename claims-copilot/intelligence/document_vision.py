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
import hashlib
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

_MARINE_VISION_PROMPT = """You are a marine cargo claims forensics analyst working for a cargo insurer.
You inspect evidence submitted with cargo claims — most commonly survey photographs of
damaged cargo, containers, seals and packaging, but also shipping documents: bills of
lading, commercial invoices, packing lists, survey reports, Equipment Interchange Receipts
(EIRs) and delivery receipts. Your job is to assess whether the image is authentic,
consistent supporting evidence or shows signs of fabrication, reuse, or tampering, and
whether it shows conditions (e.g. insufficient packing) that matter for coverage under the
Institute Cargo Clauses.

First decide what KIND of image this is (a survey/damage photograph, or a document scan).
Then evaluate it against ALL 13 checks below. For EACH check, provide a JSON object with
your finding. If a check does not apply to this image type (e.g. a font check on a cargo
photo), mark it passed=true with a short "not applicable for this image type" explanation.

THE 13 EVIDENCE CHECKS:

DOC-001  Digital Manipulation — Signs of photo editing: cloning, warped edges, mismatched lighting/shadows, copy-pasted regions?
DOC-002  Damage Inconsistent with Claimed Cause — Does the visible damage fail to match the claimed loss mechanism (e.g. "breakage in transit" but crates and packaging are pristine; "wet damage" with no water staining, tide marks or corrosion)?
DOC-003  Stock or Reused Image — Does this look like a stock photo, a watermarked internet image, or a picture reused from another claim rather than an original survey photograph?
DOC-004  Capture Date/Location Conflict — Visible timestamps, watermarks or surroundings that conflict with the voyage dates, the discharge port or the survey location?
DOC-005  Missing Shipment Identifiers — For a survey photo: is there NO visible container number, seal number, shipping marks or package numbering tying the cargo to this shipment?
DOC-006  Packing/Stowage Condition — Does the photo show insufficient or unsuitable packing, crating, dunnage or lashing (relevant to the ICC insufficient-packing exclusion) rather than an insured transit peril?
DOC-007  Font Inconsistency — For a document, are there multiple font styles or families in fields that should be uniform (suggesting edited weights, quantities or values)? Compare each figure's typeface, weight, size and ink colour with the surrounding text in the same table or block — e.g. one monospaced figure among proportional text, or darker/bluer ink on a few values.
DOC-008  Altered Figures or Dates — Do any weights, package counts, unit prices, values, B/L numbers or dates show overwriting, misalignment or digit tampering? On scanned pages, look closely for clean bright-white rectangles behind individual figures (a patch pasted over the original), sharper edges than the rest of the scan, or text tilted or offset from its neighbours' baseline.
DOC-009  Editable/Template Format — Does a bill of lading, invoice or survey report look self-made (Word/spreadsheet template) rather than issued on the carrier's, seller's or surveyor's own form?
DOC-010  Missing Official Markings — Does a document lack expected markings: carrier name and B/L number, "shipped on board" notation and date, signature on behalf of the carrier or master, surveyor letterhead and report number, invoice number?
DOC-011  Signature/Stamp Anomaly — Does any signature or company chop/stamp look pasted, photocopied or inconsistent with a genuine issued document?
DOC-012  Screenshot/Forwarded Submission — Is the image a screenshot, a photo of a screen, or a forwarded artefact rather than an original document or photograph?
DOC-013  Cross-Document Mismatch — Do visible details (container or seal number, package count, gross weight, consignee, vessel/voyage, cargo description) conflict with each other or with the shipment they are claimed to belong to?

RESPOND WITH ONLY valid JSON — no markdown fences, no commentary outside the JSON.
Use this exact structure:

{
  "checks": [
    {
      "check_id": "DOC-001",
      "check_name": "Digital Manipulation",
      "passed": true,
      "severity": "INFO",
      "explanation": "No signs of editing; lighting and edges are consistent."
    }
  ],
  "overall_assessment": "Brief 1-2 sentence summary of whether this evidence appears legitimate.",
  "confidence": 0.92
}

Severity values: "CRITICAL" for high-risk failures, "WARNING" for medium, "INFO" for low/pass.
Set passed=true if the check finds NO issues, passed=false if an issue IS detected.
"""

_VISION_PROMPT = _MARINE_VISION_PROMPT

# Vision results are cached on disk, keyed by image bytes + prompt + model, so a
# rehearsed demo replays identical findings without a live Bedrock call.
# Set VISION_CACHE=false to force fresh analysis.
_CACHE_DIR = Path(__file__).resolve().parent.parent / "vision_cache"
_CACHE_ENABLED = os.getenv("VISION_CACHE", "true").strip().lower() not in ("false", "0", "no")


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


def _cache_path(image_bytes: bytes) -> Path:
    digest = hashlib.sha256(image_bytes + _VISION_PROMPT.encode() + _VISION_MODEL.encode()).hexdigest()
    return _CACHE_DIR / f"{digest[:32]}.json"


def _dhash(path: Path, size: int = 8) -> Optional[int]:
    """64-bit difference hash — survives resizing and re-compression of a photo."""
    try:
        img = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
    except OSError:
        return None
    px = list(img.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def find_duplicate_images(claim_id: str, max_distance: int = 6,
                          images_dir: Optional[Path] = None) -> List[Dict]:
    """Find images filed on OTHER claims that are near-duplicates of this claim's images.

    Deterministic (no LLM): compares perceptual hashes across the whole images folder.
    Returns [{"image", "other_image", "other_key", "distance"}], where other_key is the
    lowercase-alphanumeric claim key of the other file (e.g. "mc2988").
    """
    root = images_dir or _IMAGES_DIR
    own = find_claim_images(claim_id, root)
    if not own:
        return []
    key = _claim_id_to_image_key(claim_id)
    own_names = {p.name for p in own}
    others = [p for p in root.iterdir()
              if p.suffix.lower() in _IMAGE_EXTENSIONS and p.name not in own_names]

    own_hashes = [(p, _dhash(p)) for p in own]
    matches = []
    for other in others:
        other_key = other.stem.split("_")[0].lower()
        if other_key == key:
            continue
        oh = _dhash(other)
        if oh is None:
            continue
        for p, h in own_hashes:
            if h is None:
                continue
            distance = bin(h ^ oh).count("1")
            if distance <= max_distance:
                matches.append({"image": p.name, "other_image": other.name,
                                "other_key": other_key, "distance": distance})
    return matches


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
    image_bytes, media_type = _load_image(image_path)

    cache_path = _cache_path(image_bytes)
    if _CACHE_ENABLED and cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                logger.info("Vision cache hit for %s", image_path.name)
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    client = bedrock_client or _get_bedrock_client()
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
        parsed = json.loads(cleaned)
        if _CACHE_ENABLED:
            try:
                _CACHE_DIR.mkdir(exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
            except OSError as e:
                logger.warning("Could not write vision cache: %s", e)
        return parsed

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
    skip_images: Optional[set] = None,
) -> Optional[List[DocCheckResult]]:
    """
    Run the 13 DOC checks using Claude Haiku 4.5 vision on the claim's document image(s).

    skip_images: file names to leave out — images already proven reused by the hash
    check are reported by rule R-009, so a model opinion on them adds nothing.

    Returns:
        List[DocCheckResult] if an image was found and analyzed successfully.
        None if no image exists for this claim (caller should fall back to metadata checks).
    """
    images = [p for p in find_claim_images(claim_id, images_dir)
              if p.name not in (skip_images or set())]
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
