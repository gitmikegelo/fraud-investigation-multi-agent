"""Client for the external D.E.C.R.E.E damage-evaluation service.

DECREE accepts a vehicle damage photo and returns a structured damage assessment
with cost estimates. See LLM_CONTEXT.md for the full API contract.

    POST http://localhost:3000/api/v1/assess  (multipart, no auth)
      file    — the image (required)
      message — optional text context
      mode    — "short" (3-5 sentence summary) or "full" (detailed markdown report)
"""

import os
from pathlib import Path
from typing import Optional

import requests

from intelligence.document_vision import find_claim_images

DECREE_URL = os.environ.get("DECREE_URL", "http://localhost:3000/api/v1/assess")

# Multipart content-type per file extension.
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _media_type(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def run_decree_assessment(
    claim_id: str,
    mode: str = "short",
    message: Optional[str] = None,
    images_dir: Optional[Path] = None,
) -> Optional[dict]:
    """POST the claim's damage photo to DECREE.

    Args:
        claim_id: claim whose evidence image should be assessed.
        mode: "short" for a 3-5 sentence summary, "full" for a markdown report.
        message: optional free-text context about the damage.
        images_dir: override the image search directory (mainly for tests).

    Returns:
        The DECREE `data` object (reportContent, costEstimate*, confidenceLevel,
        confidenceFactors, mode) on success, or None if no image exists or the
        request failed. Callers fall back gracefully when None.
    """
    images = find_claim_images(claim_id, images_dir)
    if not images:
        return None

    # DECREE always needs a non-empty `message` — an empty/null value makes its
    # Bedrock call fail with "text content blocks must be non-empty" (full mode
    # especially). Default to a claim-derived context line when none is supplied.
    if not message:
        message = f"Vehicle damage assessment for claim {claim_id}."

    primary = images[0]
    try:
        files = {"file": (primary.name, primary.read_bytes(), _media_type(primary))}
        data = {"mode": mode, "message": message}
        resp = requests.post(DECREE_URL, files=files, data=data, timeout=90)
        body = resp.json()
    except Exception as e:  # network error, timeout, bad JSON, etc.
        print(f"  [WARN] DECREE assessment failed for {claim_id} (mode={mode}): {e}")
        return None

    if not body.get("success"):
        print(f"  [WARN] DECREE returned unsuccessful response for {claim_id}: {body.get('error')}")
        return None

    return body.get("data")
