from pydantic import BaseModel, Field


class TicketProcessingResult(BaseModel):
    """Result of processing a single support ticket."""

    title: str = Field(
        description="Generated ticket title.",
    )
    department_id: int = Field(
        description="Identifier of the selected department.",
    )
    reasoning: str = Field(
        description="Explanation of the department selection.",
    )
    description: str = Field(
        description="Generated ticket description.",
    )
