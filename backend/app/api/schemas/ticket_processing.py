from pydantic import BaseModel, Field, field_validator


class TicketProcessingRequest(BaseModel):
    """HTTP request for generating a ticket description."""

    ticket_text: str = Field(
        min_length=1,
        max_length=4000,
        description="Original content of a single support ticket.",
    )
    department_id: int = Field(
        gt=0,
        description="ID of the department selected during ticket routing.",
    )
    template: str = Field(
        min_length=1,
        max_length=2000,
        description="Description template selected by the user.",
    )

    @field_validator("ticket_text", "template")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Reject values containing only whitespace."""
        if not value.strip():
            raise ValueError("The field must not be blank.")

        return value


class TicketProcessingResponse(BaseModel):
    """HTTP response containing the generated ticket description."""

    description: str = Field(
        description="Generated ticket description.",
    )
