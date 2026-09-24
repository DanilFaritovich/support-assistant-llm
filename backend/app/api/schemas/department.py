from pydantic import BaseModel, Field


class DepartmentResponse(BaseModel):
    """Department data returned by the HTTP API."""

    id: int = Field(description="Department identifier.")
    name: str = Field(description="Department name.")
    description: str | None = Field(
        default=None,
        description="Department responsibilities.",
    )
