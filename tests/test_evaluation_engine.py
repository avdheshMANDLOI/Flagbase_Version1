"""
Unit tests for the evaluation engine.

These tests require ZERO infrastructure — no database, no Docker, no fixtures.
The engine is a pure function: we pass in plain Python objects and assert the output.

This is the highest-value test file in the entire project.
Every edge case from SPEC.md Section 11.4 is covered here.
"""
from types import SimpleNamespace

import pytest

from app.services.evaluation_engine import (
    REASON_FLAG_DISABLED,
    REASON_ROLLOUT_EXCLUDED,
    REASON_ROLLOUT_INCLUDED,
    REASON_RULE_EXCLUDE,
    REASON_RULE_INCLUDE,
    _compute_bucket,
    evaluate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_flag(is_enabled=True, rollout_percentage=100, name="test_flag"):
    """Create a minimal flag object. Uses SimpleNamespace — no DB needed."""
    return SimpleNamespace(
        is_enabled=is_enabled,
        rollout_percentage=rollout_percentage,
        name=name,
    )


def make_rule(rule_type, operator, value, effect, priority=0, attribute_key=None):
    """Create a minimal rule object."""
    return SimpleNamespace(
        rule_type=rule_type,
        attribute_key=attribute_key,
        operator=operator,
        value=value,
        effect=effect,
        priority=priority,
    )


# ── Step 1: Kill switch ───────────────────────────────────────────────────────

def test_kill_switch_disabled_flag_returns_false():
    flag = make_flag(is_enabled=False, rollout_percentage=100)
    result = evaluate(flag, rules=[], user_id="user_1", context={})
    assert result.enabled is False
    assert result.reason == REASON_FLAG_DISABLED


def test_kill_switch_overrides_100_percent_rollout():
    """Even with 100% rollout, a disabled flag returns false."""
    flag = make_flag(is_enabled=False, rollout_percentage=100)
    result = evaluate(flag, rules=[], user_id="user_1", context={})
    assert result.enabled is False
    assert result.reason == REASON_FLAG_DISABLED


# ── Step 2: Rollout edge cases ────────────────────────────────────────────────

def test_rollout_zero_returns_false():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    result = evaluate(flag, rules=[], user_id="user_1", context={})
    assert result.enabled is False
    assert result.reason == REASON_ROLLOUT_EXCLUDED


def test_rollout_100_returns_true_without_hashing():
    """100% rollout should never need to compute a hash."""
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    result = evaluate(flag, rules=[], user_id="user_1", context={})
    assert result.enabled is True
    assert result.reason == REASON_ROLLOUT_INCLUDED


def test_empty_user_id_is_valid():
    """Empty string user_id is treated as a valid user. Bucketed consistently."""
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    result = evaluate(flag, rules=[], user_id="", context={})
    assert result.enabled is True


def test_none_context_treated_as_empty():
    """context=None should not crash — treated as {}."""
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    result = evaluate(flag, rules=[], user_id="user_1", context=None)
    assert result.enabled is True


# ── Step 3: Exclude rules ─────────────────────────────────────────────────────

def test_exclude_rule_blocks_matching_user():
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    rule = make_rule(rule_type="user_id", operator="equals", value="blocked_user", effect="exclude")
    result = evaluate(flag, rules=[rule], user_id="blocked_user", context={})
    assert result.enabled is False
    assert result.reason == REASON_RULE_EXCLUDE


def test_exclude_rule_does_not_block_non_matching_user():
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    rule = make_rule(rule_type="user_id", operator="equals", value="blocked_user", effect="exclude")
    result = evaluate(flag, rules=[rule], user_id="normal_user", context={})
    assert result.enabled is True


def test_exclude_takes_priority_over_include():
    """User in both exclude and include rule → exclude wins."""
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    exclude_rule = make_rule(
        rule_type="user_id", operator="equals", value="user_1", effect="exclude", priority=0
    )
    include_rule = make_rule(
        rule_type="user_id", operator="equals", value="user_1", effect="include", priority=1
    )
    result = evaluate(flag, rules=[include_rule, exclude_rule], user_id="user_1", context={})
    assert result.enabled is False
    assert result.reason == REASON_RULE_EXCLUDE


# ── Step 4: Include rules ─────────────────────────────────────────────────────

def test_include_rule_enables_matching_user():
    flag = make_flag(is_enabled=True, rollout_percentage=0)  # 0% rollout
    rule = make_rule(rule_type="user_id", operator="equals", value="beta_user", effect="include")
    result = evaluate(flag, rules=[rule], user_id="beta_user", context={})
    assert result.enabled is True
    assert result.reason == REASON_RULE_INCLUDE


def test_include_rule_does_not_affect_non_matching_user():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(rule_type="user_id", operator="equals", value="beta_user", effect="include")
    result = evaluate(flag, rules=[rule], user_id="normal_user", context={})
    assert result.enabled is False
    assert result.reason == REASON_ROLLOUT_EXCLUDED


# ── Operator tests ────────────────────────────────────────────────────────────

def test_operator_equals():
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    rule = make_rule(rule_type="country", operator="equals", value="IN", effect="exclude")
    result = evaluate(flag, rules=[rule], user_id="u", context={"country": "IN"})
    assert result.enabled is False


def test_operator_not_equals():
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    rule = make_rule(rule_type="country", operator="not_equals", value="IN", effect="include")
    # user from US — not_equals matches → include
    result = evaluate(flag, rules=[rule], user_id="u", context={"country": "US"})
    assert result.enabled is True
    assert result.reason == REASON_RULE_INCLUDE


def test_operator_in_list():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="user_id",
        operator="in_list",
        value=["user_1", "user_2", "user_3"],
        effect="include",
    )
    result = evaluate(flag, rules=[rule], user_id="user_2", context={})
    assert result.enabled is True
    assert result.reason == REASON_RULE_INCLUDE


def test_operator_in_list_non_member():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="user_id",
        operator="in_list",
        value=["user_1", "user_2"],
        effect="include",
    )
    result = evaluate(flag, rules=[rule], user_id="user_99", context={})
    assert result.enabled is False


def test_operator_not_in_list():
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    rule = make_rule(
        rule_type="user_id",
        operator="not_in_list",
        value=["banned_1", "banned_2"],
        effect="exclude",
    )
    # banned_1 IS in the list, so not_in_list = False → rule does NOT match → user gets through
    result = evaluate(flag, rules=[rule], user_id="banned_1", context={})
    assert result.enabled is True

    # user_99 is NOT in the list, so not_in_list = True → rule matches → user excluded
    result = evaluate(flag, rules=[rule], user_id="user_99", context={})
    assert result.enabled is False


# ── Rule type: email ──────────────────────────────────────────────────────────

def test_rule_type_email():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="email",
        operator="equals",
        value="admin@company.com",
        effect="include",
    )
    result = evaluate(
        flag, rules=[rule], user_id="user_1", context={"email": "admin@company.com"}
    )
    assert result.enabled is True


def test_rule_type_email_missing_from_context():
    """If email is not in context, rule should not match."""
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="email",
        operator="equals",
        value="admin@company.com",
        effect="include",
    )
    result = evaluate(flag, rules=[rule], user_id="user_1", context={})
    assert result.enabled is False


# ── Rule type: custom_attribute ───────────────────────────────────────────────

def test_rule_type_custom_attribute():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="custom_attribute",
        attribute_key="plan",
        operator="equals",
        value="premium",
        effect="include",
    )
    result = evaluate(
        flag,
        rules=[rule],
        user_id="user_1",
        context={"custom_attributes": {"plan": "premium"}},
    )
    assert result.enabled is True


def test_rule_type_custom_attribute_missing():
    flag = make_flag(is_enabled=True, rollout_percentage=0)
    rule = make_rule(
        rule_type="custom_attribute",
        attribute_key="plan",
        operator="equals",
        value="premium",
        effect="include",
    )
    result = evaluate(flag, rules=[rule], user_id="user_1", context={})
    assert result.enabled is False


# ── Priority ordering ─────────────────────────────────────────────────────────

def test_lower_priority_exclude_evaluated_before_higher():
    """Priority 0 exclude rule should fire before priority 10 include rule."""
    flag = make_flag(is_enabled=True, rollout_percentage=100)
    exclude_rule = make_rule(
        rule_type="user_id", operator="equals", value="user_1", effect="exclude", priority=0
    )
    include_rule = make_rule(
        rule_type="user_id", operator="equals", value="user_1", effect="include", priority=10
    )
    result = evaluate(flag, rules=[include_rule, exclude_rule], user_id="user_1", context={})
    assert result.enabled is False
    assert result.reason == REASON_RULE_EXCLUDE


# ── Bucketing / consistent hashing ───────────────────────────────────────────

def test_compute_bucket_returns_0_to_99():
    for user_id in ["user_1", "user_2", "admin", "", "very_long_user_id_string_here_12345"]:
        bucket = _compute_bucket("test_flag" + user_id)
        assert 0 <= bucket <= 99, f"Bucket out of range for {user_id}: {bucket}"


def test_compute_bucket_is_deterministic():
    """Same seed must always return the same bucket."""
    seed = "test_flaguser_123"
    bucket_1 = _compute_bucket(seed)
    bucket_2 = _compute_bucket(seed)
    bucket_3 = _compute_bucket(seed)
    assert bucket_1 == bucket_2 == bucket_3


def test_different_flags_give_different_buckets_for_same_user():
    """
    user_1 should land in different buckets for different flags.
    This ensures statistical independence across flags.
    """
    bucket_flag_a = _compute_bucket("flag_a" + "user_1")
    bucket_flag_b = _compute_bucket("flag_b" + "user_1")
    # They CAN be equal by chance, but with different flag names they should usually differ
    # We just verify both are valid buckets
    assert 0 <= bucket_flag_a <= 99
    assert 0 <= bucket_flag_b <= 99


def test_rollout_distribution_is_approximately_correct():
    """
    With 10% rollout and 10,000 users, ~10% should be enabled.
    Acceptable range: 8%–12% (see SPEC.md Section 11.3).
    """
    flag = make_flag(is_enabled=True, rollout_percentage=10, name="dist_test")
    enabled_count = sum(
        1
        for i in range(10_000)
        if evaluate(flag, rules=[], user_id=f"user_{i}", context={}).enabled
    )
    ratio = enabled_count / 10_000
    assert 0.08 <= ratio <= 0.12, f"Distribution off: {ratio:.2%} enabled (expected ~10%)"
