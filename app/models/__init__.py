"""
Import every model here so Alembic's autogenerate (and anything else that
needs the full metadata) discovers all tables via Base.metadata.
"""
from app.models.ab_test import ABTest
from app.models.ab_variant import ABVariant
from app.models.api_key import APIKey
from app.models.conversion_event import ConversionEvent
from app.models.evaluation_event import EvaluationEvent
from app.models.flag import Flag
from app.models.flag_rule import FlagRule
from app.models.project import Project
from app.models.user import User

__all__ = [
    "ABTest",
    "ABVariant",
    "APIKey",
    "ConversionEvent",
    "EvaluationEvent",
    "Flag",
    "FlagRule",
    "Project",
    "User",
]
