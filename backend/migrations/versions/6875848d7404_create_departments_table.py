import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

# Revision identifiers.
revision: str = "6875848d7404"

down_revision: str | Sequence[str] | None = None

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


# Database table definition for data insertion.
departments_table = sa.table(
    "departments",
    sa.column("name", sa.String(length=255)),
    sa.column("description", sa.Text()),
)


def load_departments() -> list[dict[str, str]]:
    """
    Load and validate the initial department data
    from the JSON configuration file.
    """
    project_root = Path(__file__).resolve().parents[2]

    json_path = project_root / "resources" / "departments.json"

    with json_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        departments = json.load(file)

    if not isinstance(departments, list):
        raise ValueError("Department configuration must be a JSON array.")

    if not departments:
        raise ValueError("Department configuration must not be empty.")

    validated_departments = []
    department_names = set()

    for department in departments:
        if not isinstance(department, dict):
            raise ValueError("Each department must be a JSON object.")

        name = department.get("name")
        description = department.get("description")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Department name must be a non-empty string.")

        if len(name) > 255:
            raise ValueError("Department name must not exceed 255 characters.")

        if not isinstance(description, str):
            raise ValueError("Department description must be a string.")

        if name.casefold() in department_names:
            raise ValueError(f"Duplicate department name: {name}")

        department_names.add(name.casefold())

        validated_departments.append(
            {
                "name": name,
                "description": description,
            }
        )

    return validated_departments


def upgrade() -> None:
    """Create and populate the departments table."""

    departments = load_departments()

    op.create_table(
        "departments",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.bulk_insert(
        departments_table,
        departments,
    )


def downgrade() -> None:
    """Remove the departments table."""

    op.drop_table("departments")
