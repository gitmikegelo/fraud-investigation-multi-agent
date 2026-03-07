"""
Demo Mode Configuration

Set DEMO_MODE=true as an environment variable (or in .env) to enable
a fully deterministic, hardcoded investigation workflow that does NOT
call any LLM or Bedrock APIs.

The demo scenario: the dossier rejects the investigation twice
(insufficient evidence), then accepts it on the third attempt.
"""

import os


def is_demo_mode() -> bool:
    """Check if the application is running in demo mode."""
    return os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes")
