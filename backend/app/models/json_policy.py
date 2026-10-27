
from pydantic import BaseModel, Field
class UIGenerationRequest(BaseModel):
    policy_text: str = Field(
        ...,
        min_length=1,
        description="The policy content to transform into UI JSON.",
    )