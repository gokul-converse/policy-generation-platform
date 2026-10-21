
"""Write generated skill content to versioned Markdown files."""

from pathlib import Path

import yaml

from app.common.logger import get_logger
from app.config.settings import settings
from app.models.skills import GeneratedSkill

logger = get_logger(__name__)


def write_skill_file(
    generated_skill: GeneratedSkill,
    skill_id: str,
    version: int,
) -> str:
    """Write a skill to SKILL.md and return its relative path."""

    skills_root = Path(settings.generated_skills_dir).resolve()
    logger.info(
        "Writing skill file for skill %s version %d.",
        skill_id,
        version,
    )

    relative_path = Path(skill_id) / f"v{version}" / "SKILL.md"
    file_path = (skills_root / relative_path).resolve()

    # Prevent writing outside the configured skills directory.
    if not file_path.is_relative_to(skills_root):
        logger.error(
            "Refusing to write skill %s version %d outside the "
            "skills directory.",
            skill_id,
            version,
        )
        raise ValueError("Skill file path escapes the skills directory.")

    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        logger.warning(
            "Skill file already exists for skill %s version %d.",
            skill_id,
            version,
        )
        raise FileExistsError(
            f"Skill file already exists: {file_path}"
        )

    frontmatter = {
        "name": generated_skill.name,
        "description": generated_skill.description,
        "metadata": {
            "requirement_ids": generated_skill.requirement_ids,
        },
    }

    yaml_content = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip()

    markdown_body = generated_skill.instructions.strip()

    content = (
        "---\n"
        f"{yaml_content}\n"
        "---\n\n"
        f"{markdown_body}\n"
    )

    file_path.write_text(content, encoding="utf-8")
    logger.info(
        "Wrote skill file for skill %s version %d at %s.",
        skill_id,
        version,
        relative_path.as_posix(),
    )

    return relative_path.as_posix()
