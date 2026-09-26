from typing import Protocol


class LLMQuotaPort(Protocol):
    """Consume shared capacity for an expensive LLM operation."""

    async def consume(self, client_id: str) -> None:
        """Consume one operation or raise when quota is unavailable/exhausted."""
        ...
