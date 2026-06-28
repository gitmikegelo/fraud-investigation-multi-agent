"""Domain registry and active-plugin resolver.

DOMAIN_REGISTRY is populated by importing each domain's PLUGIN.
Today it is empty scaffolding — domains/car/ is wired in WS4.

Usage:
    from core.registry import get_active_plugin
    PLUGIN = get_active_plugin()
"""

from __future__ import annotations

import os
from typing import Dict

from core.contracts import DomainPlugin

DOMAIN_REGISTRY: Dict[str, DomainPlugin] = {}


def get_active_plugin() -> DomainPlugin:
    """Return the plugin named by DOMAIN_MODE (default: car_insurance)."""
    name = os.getenv("DOMAIN_MODE", "car_insurance")
    if name not in DOMAIN_REGISTRY:
        available = list(DOMAIN_REGISTRY.keys()) or ["(none registered yet)"]
        raise KeyError(
            f"DOMAIN_MODE='{name}' not found in DOMAIN_REGISTRY. "
            f"Available: {available}"
        )
    return DOMAIN_REGISTRY[name]


def register_plugin(plugin: DomainPlugin) -> None:
    """Add a plugin to the registry (called from each domain's __init__.py)."""
    DOMAIN_REGISTRY[plugin.name] = plugin
