# from pydantic import BaseModel, Field
# class UIGenerationRequest(BaseModel):
#     policy_text: str = Field(
#         ...,
#         min_length=1,
#         description="The policy content to transform into UI JSON.",
#     )



from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class UIGenerationRequest(BaseModel):
    policy_text: str | None = Field(
        default=None,
        min_length=1,
        description="Direct policy text for testing.",
    )

    policy_id: UUID | None = Field(
        default=None,
        description="Unique ID of the policy.",
    )

    version: int | None = Field(
        default=None,
        ge=1,
        description="Version number of the policy.",
    )

    @model_validator(mode="after")
    def validate_request(self):
        # Direct policy text mode
        if self.policy_text is not None:
            if self.policy_id is not None or self.version is not None:
                raise ValueError(
                    "Provide either policy_text or policy_id with version."
                )
            return self

        # Database lookup mode
        if self.policy_id is None or self.version is None:
            raise ValueError(
                "Provide either policy_text or both policy_id and version."
            )

        return self