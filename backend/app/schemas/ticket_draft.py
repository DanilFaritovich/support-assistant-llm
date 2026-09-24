from pydantic import BaseModel, ConfigDict, Field


class TicketDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        description=(
            "A complete and structured ticket description "
            "generated from the original ticket text "
            "according to the provided template."
        )
    )
