"""Write generated skill content to versioned Markdown files."""

from pathlib import Path
from uuid import UUID

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
    """Write a skill to SKILL.md and return its relative path.

    Files are stored using this layout:
        generated_skills/<skill_id>/v<version>/SKILL.md

    Existing files are never overwritten. If writing fails, a partially
    created file is removed on a best-effort basis.
    """
    if version < 1:
        raise ValueError("Skill version must be greater than zero.")

    try:
        normalized_skill_id = str(UUID(skill_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("skill_id must be a valid UUID.") from exc

    skills_root = settings.generated_skills_path.resolve()

    relative_path = (
        Path(normalized_skill_id)
        / f"v{version}"
        / "SKILL.md"
    )
    file_path = (skills_root / relative_path).resolve()

    # Prevent writing outside the configured generated-skills directory.
    try:
        file_path.relative_to(skills_root)
    except ValueError as exc:
        logger.error(
            "Refusing to write skill %s version %d outside the skills directory.",
            normalized_skill_id,
            version,
        )
        raise ValueError(
            "Skill file path escapes the skills directory."
        ) from exc

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

    file_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Writing skill file for skill %s version %d.",
        normalized_skill_id,
        version,
    )

    # Track whether this call successfully created the file so cleanup
    # never removes a file that existed before this operation.
    created_file = False

    try:
        # Exclusive creation prevents silently overwriting an existing file.
        with file_path.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as file:
            created_file = True
            file.write(content)

    except FileExistsError:
        logger.warning(
            "Skill file already exists for skill %s version %d.",
            normalized_skill_id,
            version,
        )
        raise

    except OSError:
        logger.exception(
            "Failed to write skill file for skill %s version %d.",
            normalized_skill_id,
            version,
        )

        if created_file:
            try:
                # Revalidate the path before deleting the partial file.
                resolved_path = file_path.resolve()
                resolved_path.relative_to(skills_root)

                if resolved_path.is_file():
                    resolved_path.unlink()

            except (OSError, ValueError):
                logger.exception(
                    "Could not clean up partially written skill file: %s",
                    file_path,
                )

        raise

    logger.info(
        "Wrote skill file for skill %s version %d at %s.",
        normalized_skill_id,
        version,
        relative_path.as_posix(),
    )

    return relative_path.as_posix()
