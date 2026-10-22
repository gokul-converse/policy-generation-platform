
"""Tests for writing generated skills to Markdown files."""

import yaml

from app.models.skills import GeneratedSkill
from app.services.skill_file_service import write_skill_file


def test_write_skill_file_creates_valid_frontmatter(
    tmp_path,
    monkeypatch,
):
    """Write valid YAML frontmatter and preserve the Markdown body."""

    from app.config.settings import settings

    monkeypatch.setattr(
        settings,
        "generated_skills_dir",
        str(tmp_path),
    )

    skill = GeneratedSkill(
        name="annual-leave-policy",
        description="Defines annual leave entitlement.",
        instructions=(
            "# Annual Leave Policy\n\n"
            "## Purpose\n"
            "Define the supplied leave entitlement.\n\n"
            "## Instructions\n"
            "- Preserve the specified entitlement.\n\n"
            "## Source Requirements\n"
            "- REQ-001: Employees receive 20 days of annual leave."
        ),
        requirement_ids=["REQ-001"],
    )

    relative_path = write_skill_file(
        generated_skill=skill,
        skill_id="test-skill-id",
        version=1,
    )

    file_path = tmp_path / relative_path
    content = file_path.read_text(encoding="utf-8")

    assert content.startswith("---\n")

    parts = content.split("---", 2)
    assert len(parts) == 3

    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["name"] == "annual-leave-policy"
    assert frontmatter["description"] == (
        "Defines annual leave entitlement."
    )
    assert frontmatter["metadata"]["requirement_ids"] == ["REQ-001"]

    markdown_body = parts[2]
    assert "# Annual Leave Policy" in markdown_body
    assert "## Purpose" in markdown_body
    assert "## Instructions" in markdown_body
    assert "## Source Requirements" in markdown_body
    assert "20 days" in markdown_body
