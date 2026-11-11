from functools import lru_cache
from pathlib import Path

from app.schemas.workspace import WorkspaceDefaults


@lru_cache(maxsize=1)
def load_workspace_defaults() -> WorkspaceDefaults:
    """Load repository-owned localized examples and templates once per process."""
    path = Path(__file__).resolve().parents[2] / "resources" / "workspace.json"
    return WorkspaceDefaults.model_validate_json(path.read_text(encoding="utf-8"))
