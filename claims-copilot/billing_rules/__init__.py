"""
Billing rules module for Claims Investigation Copilot.
Provides semantic search over CMS/OIG guidelines.
"""

from .index import (
    BillingRulesIndex,
    get_billing_rules_index,
    search_billing_rules,
)

__all__ = [
    'BillingRulesIndex',
    'get_billing_rules_index',
    'search_billing_rules',
]
