"""
Pydantic schemas for targeting rule routes.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


# v1 supported operators only. 'contains' is v2 — see SPEC.md Section 11.2.
SUPPORTED_OPERATORS = {"equals", "not_equals", "in_list", "not_in_list"}
SUPPORTED_RULE_TYPES = {"user_id", "email", "country", "custom_attribute"}
SUPPORTED_EFFECTS = {"include", "exclude"}


class RuleCreate(BaseModel):
    rule_type: str
    attribute_key: str | None = None   # required when rule_type == "custom_attribute"
    operator: str
    value: str | list                  # string for scalar operators, list for in_list/not_in_list
    effect: str
    priority: int = 0

    @model_validator(mode="after")
    def validate_rule(self) -> "RuleCreate":
        if self.rule_type not in SUPPORTED_RULE_TYPES:
            raise ValueError(f"rule_type must be one of {SUPPORTED_RULE_TYPES}")

        if self.operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"operator must be one of {SUPPORTED_OPERATORS}")

        if self.effect not in SUPPORTED_EFFECTS:
            raise ValueError(f"effect must be one of {SUPPORTED_EFFECTS}")

        if self.rule_type == "custom_attribute" and not self.attribute_key:
            raise ValueError("attribute_key is required when rule_type is 'custom_attribute'")

        # in_list / not_in_list require a list value
        if self.operator in ("in_list", "not_in_list") and not isinstance(self.value, list):
            raise ValueError(f"operator '{self.operator}' requires value to be a list")

        # equals / not_equals require a string value
        if self.operator in ("equals", "not_equals") and not isinstance(self.value, str):
            raise ValueError(f"operator '{self.operator}' requires value to be a string")

        return self


class RuleResponse(BaseModel):
    id: uuid.UUID
    flag_id: uuid.UUID
    rule_type: str
    attribute_key: str | None
    operator: str
    value: str | list
    effect: str
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}
