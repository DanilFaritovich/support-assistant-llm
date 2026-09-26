import logging
from typing import Any

from openai import APIError, AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMResponseError(Exception):
    """Raised when the LLM returns an unusable response."""


class OpenRouterBaseConnector:
    """Provide shared access to an OpenAI-compatible chat API."""

    def __init__(
        self,
        client: AsyncOpenAI,
        models: list[str],
    ) -> None:
        if not models or any(not model.strip() for model in models):
            logger.error("LLM connector initialization failed: models are missing.")
            raise ValueError("At least one LLM model must be configured.")

        self._client = client
        self._models = models

        logger.debug("LLM connector initialized.")

    async def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        schema_name: str,
    ) -> str:
        """Send a chat request and return the assistant's text."""
        logger.debug("Sending chat completion request to the LLM.")
        extra_body: dict[str, Any] = {
            "provider": {"require_parameters": True},
        }
        if len(self._models) > 1:
            extra_body["models"] = self._models[1:]

        try:
            completion = await self._client.chat.completions.create(
                model=self._models[0],
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": response_schema,
                    },
                },
                extra_body=extra_body,
            )

        except APIError as exc:
            logger.error(
                "LLM API request failed.",
                extra={
                    "event": "llm_api_request_failed",
                    "error_type": type(exc).__name__,
                },
            )
            raise

        if not completion.choices:
            logger.warning("LLM response validation failed: no completion choices.")
            raise LLMResponseError("The LLM returned no completion choices.")

        choice = completion.choices[0]

        if choice.finish_reason == "length":
            logger.warning("LLM response validation failed: completion was truncated.")
            raise LLMResponseError("The LLM response was truncated.")

        content = choice.message.content

        if not content:
            logger.warning("LLM response validation failed: message content is empty.")
            raise LLMResponseError("The LLM returned an empty response.")

        logger.debug("Chat completion response received successfully.")

        return content
