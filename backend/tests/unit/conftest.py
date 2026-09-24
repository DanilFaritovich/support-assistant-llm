from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncOpenAI

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
)
from app.connectors.openrouter_ticket_routing_connector import (
    OpenRouterTicketRoutingConnector,
)


@pytest.fixture
def llm_client() -> MagicMock:
    """Create a mocked asynchronous OpenAI client."""
    client = MagicMock(spec=AsyncOpenAI)

    client.chat.completions.create = AsyncMock()
    client.close = AsyncMock()

    return client


@pytest.fixture
def routing_connector(
    llm_client: MagicMock,
) -> OpenRouterTicketRoutingConnector:
    """Create a routing connector using the mocked LLM client."""
    return OpenRouterTicketRoutingConnector(
        client=llm_client,
        models=["test-model:free", "fallback-model:free"],
    )


@pytest.fixture
def drafting_connector(
    llm_client: MagicMock,
) -> OpenRouterTicketDraftingConnector:
    """Create a drafting connector using the mocked LLM client."""
    return OpenRouterTicketDraftingConnector(
        client=llm_client,
        models=["test-model:free", "fallback-model:free"],
    )
