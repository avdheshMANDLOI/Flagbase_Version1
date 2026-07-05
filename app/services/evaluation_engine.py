"""
FlagBase Evaluation Engine.

This module is a pure function — it takes data as input and returns a result.
It never touches the database, cache, or any I/O directly.

Why pure?
  - Fully testable without mocking anything
  - Easy to reason about: same input always gives same output
  - The router/service handles I/O (DB fetch, event write); the engine handles logic

Algorithm (see SPEC.md Section 11.1):
  Step 1: Kill switch — if flag is disabled, return false immediately
  Step 2: Exclude rules — if user matches any exclude rule, return false
  Step 3: Include rules — if user matches any include rule, return true
  Step 4: Rollout bucketing — hash user into a bucket (0-99), compare with rollout_percentage
"""
from dataclasses import dataclass

import mmh3


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class EvaluationResult:
    enabled: bool
    reason: str
    variant: str | None = None


# ── Reason constants ──────────────────────────────────────────────────────────

REASON_FLAG_DISABLED = "flag_disabled"
REASON_RULE_EXCLUDE = "rule_match_exclude"
REASON_RULE_INCLUDE = "rule_match_include"
REASON_ROLLOUT_INCLUDED = "rollout_included"
REASON_ROLLOUT_EXCLUDED = "rollout_excluded"


# ── Main evaluation function ──────────────────────────────────────────────────

def evaluate(flag, rules: list, user_id: str, context: dict | None) -> EvaluationResult:
    """
    Evaluate a feature flag for a given user.

    Args:
        flag:     SQLAlchemy Flag ORM object (or any object with .is_enabled,
                  .rollout_percentage attributes)
        rules:    List of FlagRule ORM objects for this flag
        user_id:  The user identifier string (can be empty string — always valid)
        context:  Optional dict with keys like 'email', 'country', 'custom_attributes'

    Returns:
        EvaluationResult with enabled (bool), reason (str), variant (str | None)
    """
    if context is None:
        context = {}

    # Step 1 — Kill switch
    # The master on/off toggle overrides everything else.
    if not flag.is_enabled:
        return EvaluationResult(enabled=False, reason=REASON_FLAG_DISABLED)

    # Sort rules by priority ascending (lower number = evaluated first)
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    # Step 2 — Exclude rules (evaluated before include rules)
    # If ANY exclude rule matches, the user is blocked regardless of include rules.
    for rule in sorted_rules:
        if rule.effect == "exclude" and _rule_matches(rule, user_id, context):
            return EvaluationResult(enabled=False, reason=REASON_RULE_EXCLUDE)

    # Step 3 — Include rules
    # If ANY include rule matches, the user gets the flag immediately.
    for rule in sorted_rules:
        if rule.effect == "include" and _rule_matches(rule, user_id, context):
            return EvaluationResult(enabled=True, reason=REASON_RULE_INCLUDE)

    # Step 4 — Percentage rollout
    # No rules matched — fall through to consistent hash bucketing.
    if flag.rollout_percentage == 0:
        return EvaluationResult(enabled=False, reason=REASON_ROLLOUT_EXCLUDED)

    if flag.rollout_percentage == 100:
        return EvaluationResult(enabled=True, reason=REASON_ROLLOUT_INCLUDED)

    bucket = _compute_bucket(flag.name + user_id)
    enabled = bucket < flag.rollout_percentage
    reason = REASON_ROLLOUT_INCLUDED if enabled else REASON_ROLLOUT_EXCLUDED
    return EvaluationResult(enabled=enabled, reason=reason)


# ── Rule matching ─────────────────────────────────────────────────────────────

def _rule_matches(rule, user_id: str, context: dict) -> bool:
    """
    Check whether a single rule matches the current user + context.

    v1 operators: equals, not_equals, in_list, not_in_list
    v2 will add:  contains (substring check)
    """
    attribute_value = _get_attribute(rule, user_id, context)

    if attribute_value is None:
        # Attribute not present in context — rule cannot match
        return False

    rule_value = rule.value  # str or list, from JSONB column

    match rule.operator:
        case "equals":
            return attribute_value == rule_value
        case "not_equals":
            return attribute_value != rule_value
        case "in_list":
            return attribute_value in rule_value
        case "not_in_list":
            return attribute_value not in rule_value
        case _:
            # Unknown operator — fail safe (no match)
            return False


def _get_attribute(rule, user_id: str, context: dict) -> str | None:
    """
    Resolve the attribute value based on rule_type.

    rule_type options:
      - user_id:          the user_id passed in directly
      - email:            context["email"]
      - country:          context["country"]
      - custom_attribute: context["custom_attributes"][attribute_key]
    """
    match rule.rule_type:
        case "user_id":
            return user_id
        case "email":
            return context.get("email")
        case "country":
            return context.get("country")
        case "custom_attribute":
            custom = context.get("custom_attributes", {})
            return custom.get(rule.attribute_key) if rule.attribute_key else None
        case _:
            return None


# ── Consistent hashing / bucketing ───────────────────────────────────────────

def _compute_bucket(seed: str) -> int:
    """
    Compute a stable bucket integer (0-99) for a given seed string.

    Seed = flag_name + user_id

    Why flag_name is included:
      Without it, user "user_123" always lands in the same bucket.
      That means they'd always be included (or excluded) from every 10% rollout.
      Including flag_name gives each flag an independent distribution.

    Why MurmurHash3:
      - Non-cryptographic (fast, < 1 microsecond)
      - Excellent distribution — 10% rollout really gives ~10% of users
      - Deterministic across all machines and Python versions
      - signed=False gives us a clean 0 to 2^32-1 range

    See SPEC.md Section 11.3 for statistical verification.
    """
    hash_value = mmh3.hash(seed, signed=False)  # unsigned 32-bit int
    return hash_value % 100
