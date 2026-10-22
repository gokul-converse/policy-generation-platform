
from app.models.policy import PolicyDraft, PolicySection
from app.models.requirements import (
    Requirement,
    RequirementAnalysis,
)

analysis = RequirementAnalysis(
    domain="HR",
    requirements=[
        Requirement(
            requirement_id="REQ-001",
            text="Employees receive 20 days of annual leave per year.",
            category="entitlement",
            explicit_values=["20 days", "per year"],
            source_text="Employees receive 20 days of annual leave per year.",
        ),
        Requirement(
            requirement_id="REQ-002",
            text="Leave requests must be submitted at least 5 days before leave starts.",
            category="notice_period",
            explicit_values=["5 days"],
            source_text="Leave requests must be submitted at least 5 days before leave starts.",
        ),
    ],
)

draft = PolicyDraft(
    title="Annual Leave Policy",
    domain="HR",
    sections=[
        PolicySection(
            section_id="SEC-001",
            title="Annual Leave Entitlement",
            content="Employees receive 20 days of annual leave per year.",
            requirement_ids=["REQ-001"],
        ),
        PolicySection(
            section_id="SEC-002",
            title="Request Notice Period",
            content="Employees must submit leave requests at least 5 days before leave starts.",
            requirement_ids=["REQ-002"],
        ),
    ],
)

print("Requirements model:")
print(analysis.model_dump_json(indent=2))

print("\nPolicy model:")
print(draft.model_dump_json(indent=2))
