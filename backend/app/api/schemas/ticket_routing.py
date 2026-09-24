from pydantic import BaseModel, Field, field_validator


class TicketRoutingRequest(BaseModel):
    """HTTP request for routing a single support ticket."""

    ticket_text: str = Field(
        min_length=1,
        description="Original content of a single support ticket.",
    )

    @field_validator("ticket_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Reject ticket text containing only whitespace."""
        if not value.strip():
            raise ValueError("Ticket text must not be blank.")

        return value


class TicketRoutingResponse(BaseModel):
    """HTTP response containing the ticket routing result."""

    title: str = Field(
        description="Generated ticket title.",
    )
    department_id: int = Field(
        description="Identifier of the selected department.",
    )
    department_name: str = Field(
        description="Name of the selected department.",
    )
    reasoning: str = Field(
        description="Explanation of the department selection.",
    )
