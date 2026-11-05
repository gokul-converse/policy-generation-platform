"""Centralized skill provider configuration."""

from agent_framework import (
    FileSkillsSource,
    FilteringSkillsSource,
    SkillsProvider,
)

from app.config.settings import settings


def create_skill_generation_provider() -> SkillsProvider:
    """
    Load the configured built-in skill for the Skill Generation Agent only.

    Policy Generation must use database-generated skills through a
    separate provider.
    """
    builtin_root = settings.builtin_skills_path.parent
    configured_skill_name = settings.skill_generation_builtin_skill_name

    if not settings.skill_generation_builtin_skill_path.is_dir():
        raise FileNotFoundError(
            "Configured built-in skill directory does not exist: "
            f"{settings.skill_generation_builtin_skill_path}"
        )

    skill_file = settings.skill_generation_builtin_skill_path / "SKILL.md"

    if not skill_file.is_file():
        raise FileNotFoundError(
            f"SKILL.md not found for built-in skill: {configured_skill_name}"
        )

    source = FileSkillsSource(builtin_root)

    filtered_source = FilteringSkillsSource(
        source,
        lambda skill, context: (
            skill.frontmatter.name == configured_skill_name
        ),
    )

    return SkillsProvider(
        filtered_source,
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )
