"""Database-backed skill source for Microsoft Agent Framework."""

import json
from collections.abc import Sequence
from uuid import UUID

import yaml
from agent_framework import (
    InlineSkill,
    Skill,
    SkillFrontmatter,
    SkillsSource,
    SkillsSourceContext,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.skill_db import Skill as SkillModel
from app.models.skill_db import SkillVersion


class DatabaseSkillsSource(SkillsSource):
    """Load explicitly selected skill versions from the database."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        skill_version_ids: Sequence[UUID],
    ) -> None:
        if not skill_version_ids:
            raise ValueError(
                "At least one skill version ID must be provided."
            )

        if len(skill_version_ids) != len(set(skill_version_ids)):
            raise ValueError(
                "Duplicate skill version IDs are not allowed."
            )

        self._session_factory = session_factory
        self._skill_version_ids = tuple(skill_version_ids)

    async def get_skills(
        self,
        context: SkillsSourceContext,
    ) -> list[Skill]:
        """Retrieve exact skill versions and expose them as MAF skills."""

        async with self._session_factory() as session:
            result = await session.execute(
                select(SkillVersion, SkillModel)
                .join(
                    SkillModel,
                    SkillModel.id == SkillVersion.skill_id,
                )
                .where(
                    SkillVersion.id.in_(self._skill_version_ids)
                )
            )

            records = result.all()

        versions_by_id = {
            version.id: (version, skill)
            for version, skill in records
        }

        missing_ids = [
            version_id
            for version_id in self._skill_version_ids
            if version_id not in versions_by_id
        ]

        if missing_ids:
            raise ValueError(
                f"Requested skill versions were not found: {missing_ids}"
            )

        skills: list[Skill] = []
        selected_names: set[str] = set()

        # Preserve the explicitly requested version order.
        for version_id in self._skill_version_ids:
            version, skill_record = versions_by_id[version_id]

            if not version.content:
                raise ValueError(
                    f"Skill version {version_id} has no stored content."
                )

            normalized_name = skill_record.name.strip().casefold()

            if normalized_name in selected_names:
                raise ValueError(
                    "Multiple versions of the same skill were selected: "
                    f"{skill_record.name}"
                )

            selected_names.add(normalized_name)

            instructions, metadata = self._parse_skill_content(
                version.content
            )

            # Add database traceability metadata.
            metadata.update(
                {
                    "skill_version_id": str(version.id),
                    "skill_id": str(skill_record.id),
                    "version": str(version.version),
                }
            )

            if version.source_requirement_version_id:
                metadata["source_requirement_version_id"] = (
                    version.source_requirement_version_id
                )

            skills.append(
                InlineSkill(
                    frontmatter=SkillFrontmatter(
                        name=skill_record.name,
                        description=skill_record.description,
                        metadata=metadata,
                    ),
                    instructions=instructions,
                )
            )

        return skills

    @staticmethod
    def _parse_skill_content(
        content: str,
    ) -> tuple[str, dict[str, str]]:
        """Extract instructions and preserve YAML frontmatter metadata."""

        lines = content.splitlines()

        if not lines or lines[0].strip() != "---":
            raise ValueError(
                "Stored skill content must start with YAML frontmatter."
            )

        closing_index = None

        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break

        if closing_index is None:
            raise ValueError(
                "Stored skill content has invalid YAML frontmatter."
            )

        frontmatter_text = "\n".join(lines[1:closing_index])

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as exc:
            raise ValueError(
                "Stored skill content contains invalid YAML frontmatter."
            ) from exc

        if not isinstance(frontmatter, dict):
            raise ValueError(
                "Skill frontmatter must be a YAML mapping."
            )

        raw_metadata = frontmatter.get("metadata") or {}

        if not isinstance(raw_metadata, dict):
            raise ValueError(
                "Skill frontmatter metadata must be a mapping."
            )

        # MAF skill metadata uses string values.
        # Lists and nested values are preserved as JSON strings.
        metadata: dict[str, str] = {}

        for key, value in raw_metadata.items():
            if isinstance(value, str):
                metadata[str(key)] = value
            elif value is None:
                metadata[str(key)] = ""
            else:
                metadata[str(key)] = json.dumps(
                    value,
                    ensure_ascii=False,
                )

        instructions = "\n".join(
            lines[closing_index + 1:]
        ).strip()

        if not instructions:
            raise ValueError(
                "Stored skill instructions cannot be empty."
            )

        return instructions, metadata
