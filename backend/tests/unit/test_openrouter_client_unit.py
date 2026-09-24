from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.connectors import llm_client


def test_openrouter_client_keeps_key_server_side_and_sets_resilience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = MagicMock()
    monkeypatch.setattr(llm_client, "AsyncOpenAI", constructor)
    monkeypatch.setattr(
        llm_client.settings, "openrouter_api_key", SecretStr("server-secret")
    )
    monkeypatch.setattr(llm_client.settings, "openrouter_timeout_seconds", 45.0)
    monkeypatch.setattr(llm_client.settings, "openrouter_max_retries", 2)
    monkeypatch.setattr(
        llm_client.settings, "openrouter_site_url", "https://example.test"
    )

    client = llm_client.create_llm_client()

    assert client is constructor.return_value
    constructor.assert_called_once_with(
        base_url="https://openrouter.ai/api/v1",
        api_key="server-secret",
        timeout=45.0,
        max_retries=2,
        default_headers={
            "X-Title": "Support Assistant",
            "HTTP-Referer": "https://example.test",
        },
    )


def test_openrouter_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_client.settings, "openrouter_api_key", None)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        llm_client.create_llm_client()
