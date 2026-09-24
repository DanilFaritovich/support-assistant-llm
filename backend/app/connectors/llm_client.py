import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def create_llm_client() -> AsyncOpenAI:
    """Create an OpenAI-compatible client configured for OpenRouter."""
    if settings.openrouter_api_key is None:
        logger.error("OpenRouter client initialization failed: API key is missing.")
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    api_key = settings.openrouter_api_key.get_secret_value()
    default_headers = {"X-Title": "Support Assistant"}
    if settings.openrouter_site_url:
        default_headers["HTTP-Referer"] = settings.openrouter_site_url

    logger.debug("Initializing OpenRouter client.")

    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        timeout=settings.openrouter_timeout_seconds,
        max_retries=settings.openrouter_max_retries,
        default_headers=default_headers,
    )

    logger.info("OpenRouter client initialized.")

    return client
