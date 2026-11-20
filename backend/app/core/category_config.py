"""
Organisation-Configurable Category Priority Weights for QueueMind AI.

Default Category Priority Ranking & Business Weights:
1. Examination issues — 100
2. Fee and payment issues — 90
3. Admission issues — 80
4. Network issues — 70
5. Account and access issues — 60
6. Software issues — 50
7. Technical issues — 40
8. Hardware issues — 30
9. Other organisational issues — 20

Multi-Tenant Architecture:
- Each organisation can independently customise weights.
- Stored per organisation without leaking across tenant boundaries.
"""

import json
import os
from typing import Dict, List, Optional
from sqlalchemy import case, or_

# Standard default category business weights (100 = highest weight)
DEFAULT_CATEGORY_WEIGHTS: Dict[str, int] = {
    "Examination issues": 100,
    "Fee and payment issues": 90,
    "Admission issues": 80,
    "Network issues": 70,
    "Account and access issues": 60,
    "Software issues": 50,
    "Technical issues": 40,
    "Hardware issues": 30,
    "Other organisational issues": 20,
}

# Agreed strict category precedence order for tickets of equal severity:
# 1. Examination issues
# 2. Fee and payment issues
# 3. Admission issues
# 4. Network issues
# 5. Account and access issues
# 6. Software issues
# 7. Technical issues
# 8. Hardware issues
# 9. Other organisational issues
DEFAULT_CATEGORY_PRECEDENCE: List[str] = [
    "Examination issues",
    "Fee and payment issues",
    "Admission issues",
    "Network issues",
    "Account and access issues",
    "Software issues",
    "Technical issues",
    "Hardware issues",
    "Other organisational issues",
]

# Keywords pattern mapping for each category for robust matching
CATEGORY_SEARCH_PATTERNS: Dict[str, List[str]] = {
    "Examination issues": ["exam", "hall ticket", "admit card", "revaluation"],
    "Fee and payment issues": ["fee", "pay", "challan", "billing", "finance", "receipt"],
    "Admission issues": ["admiss", "seat", "counseling", "allotment", "enroll"],
    "Network issues": ["net", "wifi", "wi-fi", "internet", "lan", "dns", "captive"],
    "Account and access issues": ["account", "access", "login", "password", "portal", "auth", "mfa", "2fa"],
    "Software issues": ["soft", "app", "license", "matlab", "visual studio", "office", "antivirus"],
    "Technical issues": ["tech", "server", "system", "database", "api"],
    "Hardware issues": ["hard", "pc", "laptop", "monitor", "printer", "projector", "mouse", "keyboard", "smart board", "ups"],
    "Other organisational issues": ["other", "bus", "transport", "hostel", "id card", "certificate", "facilities"],
}

CONFIG_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "org_category_weights.json")
)


def _load_custom_configs() -> Dict[str, Dict[str, int]]:
    """Loads all custom organisation weights from persistent storage."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_custom_configs(configs: Dict[str, Dict[str, int]]) -> None:
    """Saves custom organisation weights to persistent storage."""
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(configs, f, indent=2)


def get_organization_weights(organization_id: Optional[int]) -> Dict[str, int]:
    """
    Returns category weights for a specific organisation.
    Merges custom organisation weights over the system defaults.
    """
    weights = dict(DEFAULT_CATEGORY_WEIGHTS)
    if not organization_id:
        return weights

    custom_all = _load_custom_configs()
    org_key = str(organization_id)
    if org_key in custom_all:
        weights.update(custom_all[org_key])

    return weights


def get_category_weight(organization_id: Optional[int], category_name: Optional[str]) -> int:
    """
    Retrieves the business weight (10-100) for a given category name in an organisation.
    Uses fuzzy matching against standard categories if needed.
    """
    if not category_name:
        return 40  # Default middle ground

    weights = get_organization_weights(organization_id)

    # 1. Exact match
    if category_name in weights:
        return weights[category_name]

    # 2. Case-insensitive / substring match
    cat_lower = category_name.lower()
    for name, w in weights.items():
        if name.lower() in cat_lower or cat_lower in name.lower():
            return w

    # Keywords fallback
    if "exam" in cat_lower:
        return weights.get("Examination issues", 100)
    if "fee" in cat_lower or "pay" in cat_lower:
        return weights.get("Fee and payment issues", 90)
    if "admiss" in cat_lower:
        return weights.get("Admission issues", 80)
    if "net" in cat_lower or "wifi" in cat_lower or "wi-fi" in cat_lower:
        return weights.get("Network issues", 70)
    if "acc" in cat_lower or "pass" in cat_lower or "login" in cat_lower:
        return weights.get("Account and access issues", 60)
    if "soft" in cat_lower or "app" in cat_lower:
        return weights.get("Software issues", 50)
    if "tech" in cat_lower:
        return weights.get("Technical issues", 40)
    if "hard" in cat_lower or "pc" in cat_lower or "print" in cat_lower:
        return weights.get("Hardware issues", 30)

    return weights.get("Other organisational issues", 20)


def get_organization_category_precedence(organization_id: Optional[int] = None) -> List[str]:
    """
    Returns the ordered category list by precedence for an organisation.
    Defaults to:
    1. Examination issues
    2. Fee and payment issues
    3. Admission issues
    4. Network issues
    5. Account and access issues
    6. Software issues
    7. Technical issues
    8. Hardware issues
    9. Other organisational issues
    If custom weights exist, categories are ordered by custom weight descending.
    """
    weights = get_organization_weights(organization_id)
    # Sort categories by configured business weight descending
    return sorted(DEFAULT_CATEGORY_PRECEDENCE, key=lambda c: weights.get(c, 0), reverse=True)


def get_category_rank(organization_id: Optional[int], category_name: Optional[str]) -> int:
    """
    Returns 1-based category precedence rank (1 = Examination, 2 = Fee, etc.).
    Used in Python logic and unit tests.
    """
    if not category_name:
        return 9
    ordered = get_organization_category_precedence(organization_id)
    cat_lower = category_name.lower().strip()

    # Exact or substring match against ordered precedence
    for rank, cat in enumerate(ordered, start=1):
        if cat.lower() in cat_lower or cat_lower in cat.lower():
            return rank

    # Keywords fallback
    for rank, cat in enumerate(ordered, start=1):
        patterns = CATEGORY_SEARCH_PATTERNS.get(cat, [])
        if any(p in cat_lower for p in patterns):
            return rank

    return 9


def build_category_rank_sql(category_expr, organization_id: Optional[int] = None):
    """
    Constructs a SQLAlchemy `case` statement returning the 1-based category rank.
    Ensures the SQL database sorts tickets natively by category precedence.
    """
    ordered = get_organization_category_precedence(organization_id)
    cases = []

    for rank, cat in enumerate(ordered, start=1):
        patterns = CATEGORY_SEARCH_PATTERNS.get(cat, [cat.lower()[:8]])
        conds = [category_expr.ilike(f"%{p}%") for p in patterns]
        if len(conds) == 1:
            cases.append((conds[0], rank))
        else:
            cases.append((or_(*conds), rank))

    return case(*cases, else_=len(ordered) + 1)


def set_organization_weights(organization_id: int, weights: Dict[str, int]) -> Dict[str, int]:
    """
    Customises category weights for an organisation.
    Enforces tenant isolation by writing only to that organisation's configuration key.
    """
    configs = _load_custom_configs()
    org_key = str(organization_id)
    org_weights = configs.get(org_key, {})

    for cat, val in weights.items():
        if isinstance(val, (int, float)):
            org_weights[cat] = max(1, min(100, int(val)))

    configs[org_key] = org_weights
    _save_custom_configs(configs)

    return get_organization_weights(organization_id)
