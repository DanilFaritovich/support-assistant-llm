from pydantic import BaseModel, ConfigDict, Field


class TicketRoutingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="A concise and descriptive title for the ticket.")

    department_id: int = Field(
        description=(
            "The unique identifier of the IT department "
            "responsible for handling the ticket."
        )
    )

    reasoning: str = Field(
        description=(
            "A brief explanation of why the selected IT department "
            "is responsible for handling the ticket."
        )
    )
