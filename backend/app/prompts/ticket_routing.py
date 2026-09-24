from pathlib import Path

PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "resources" / "prompts" / "ticket_routing.txt"
)

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()

if not SYSTEM_PROMPT:
    raise ValueError("Ticket routing system prompt must not be empty.")
