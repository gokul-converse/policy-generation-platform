import re
from typing import Any


def _validate_section_numbering(
    sections: list[Any],
) -> list[str]:
    """Check hierarchical numbering for isolated formatting tests.

    This is not a policy acceptance validator.
    Do not call this function during policy generation
    or policy modification.
    """

    issues: list[str] = []

    main_sections: list[int] = []
    subsection_counts: dict[int, int] = {}

    for section in sections:

        section_id = str(
            getattr(section, "section_id", "") or ""
        ).strip()

        if not re.fullmatch(
            r"[1-9]\d*(?:\.[1-9]\d*)?",
            section_id,
        ):
            issues.append(
                f"Invalid handbook section ID '{section_id}'. "
                "Expected numbering such as 1, 1.1 or 1.2."
            )
            continue

        # Main section
        if "." not in section_id:

            main_number = int(section_id)
            expected_main = len(main_sections) + 1

            if main_number != expected_main:
                issues.append(
                    f"Expected main section {expected_main}, "
                    f"but received {section_id}."
                )
                continue

            main_sections.append(main_number)
            subsection_counts[main_number] = 0

            continue

        # Subsection
        main_part, subsection_part = section_id.split(".")

        main_number = int(main_part)
        subsection_number = int(subsection_part)

        if main_number not in main_sections:
            issues.append(
                f"Subsection {section_id} has no preceding "
                f"main section {main_number}."
            )
            continue

        expected_subsection = (
            subsection_counts[main_number] + 1
        )

        if subsection_number != expected_subsection:
            issues.append(
                f"Expected subsection "
                f"{main_number}.{expected_subsection}, "
                f"but received {section_id}."
            )
            continue

        subsection_counts[main_number] = subsection_number

    return issues
