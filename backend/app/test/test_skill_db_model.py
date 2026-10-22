
"""Tests for the skill database model definitions."""

from app.db.session import Base
from app.models.skill_db import Skill, SkillVersion


def test_skill_tables_are_registered():
    assert "skills" in Base.metadata.tables
    assert "skill_versions" in Base.metadata.tables


def test_skill_version_has_foreign_key():
    table = SkillVersion.__table__
    foreign_keys = list(table.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "skills.id"


def test_skill_version_has_unique_version_constraint():
    constraints = SkillVersion.__table__.constraints

    assert any(
        constraint.name == "uq_skill_version"
        for constraint in constraints
    )


def test_skill_name_is_unique():
    name_column = Skill.__table__.columns["name"]

    assert name_column.unique is True
    assert name_column.nullable is False
