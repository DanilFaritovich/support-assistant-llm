from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
ItemID = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]


class WorkspaceDepartment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(gt=0, le=2147483647)
    name: Name
    description: str | None = Field(default=None, max_length=1000)


class ExampleTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: ItemID
    name: Name
    text: str = Field(min_length=1, max_length=4000)
    locale: Literal["en", "ru"] | None = None

    @model_validator(mode="after")
    def nonblank(self) -> Self:
        if not self.text.strip():
            raise ValueError("Example text must not be blank.")
        return self


class TicketTemplate(ExampleTicket):
    text: str = Field(min_length=1, max_length=2000)


class WorkspaceDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    examples: list[ExampleTicket] = Field(max_length=20)
    templates: list[TicketTemplate] = Field(min_length=1, max_length=10)


class WorkspaceData(WorkspaceDefaults):
    model_config = ConfigDict(extra="forbid")
    format_version: Literal[1] = 1
    departments: list[WorkspaceDepartment] = Field(min_length=1, max_length=20)
    default_template_id: ItemID | None = None

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        for items in (self.departments, self.examples, self.templates):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("Item IDs must be unique within each collection.")
        names = [item.name.casefold() for item in self.departments]
        if len(names) != len(set(names)):
            raise ValueError("Department names must be unique.")
        if self.default_template_id is not None and not any(
            item.id == self.default_template_id for item in self.templates
        ):
            raise ValueError("The default template must exist.")
        # Leave room for the save envelope within Nginx's existing 16 KiB limit.
        if len(self.model_dump_json().encode("utf-8")) > 15000:
            raise ValueError("Workspace settings must fit within 15,000 UTF-8 bytes.")
        return self


class WorkspaceState(BaseModel):
    retention_days: int = Field(default=90, ge=1)
    data: WorkspaceData
    revision: int = Field(ge=0)
    personalized: bool
