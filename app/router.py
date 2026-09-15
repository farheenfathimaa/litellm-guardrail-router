import logging
import os
from typing import Optional

import litellm

from app.config import MAX_OUTPUT_TOKENS_DEFAULT, PROVIDERS, ProviderConfig

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    pass


def _is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    auth_keywords = [
        "credentials",
        "credential",
        "access denied",
        "unauthorized",
        "authentication",
        "auth",
        "invalid config",
        "no api key",
        "missing key",
        "not found",
        "invalidparameterexception",
        "throttling",
        "rate limit",
        "too many requests",
        "429",
        "timeout",
        "connect timeout",
        "read timeout",
        "connection error",
        "endpointrequesttimeout",
    ]
    return any(kw in msg for kw in auth_keywords)


def _bedrock_available() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID")) and bool(
        os.environ.get("AWS_SECRET_ACCESS_KEY")
    )


def _try_provider(
    provider: ProviderConfig,
    messages: list,
    max_tokens: int,
) -> dict:
    if provider.name == "bedrock" and not _bedrock_available():
        raise RoutingError("AWS credentials not configured, skipping Bedrock")

    model_str = f"{provider.litellm_prefix}{provider.model}"
    response = litellm.completion(
        model=model_str,
        messages=messages,
        max_tokens=max_tokens,
    )

    choice = response.choices[0]
    usage = response.usage
    return {
        "content": choice.message.content,
        "provider": provider.name,
        "model": response.model,
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
    }


def route_request(
    messages: list,
    max_tokens: Optional[int] = None,
) -> dict:
    if max_tokens is None:
        max_tokens = MAX_OUTPUT_TOKENS_DEFAULT
    max_tokens = min(max_tokens, MAX_OUTPUT_TOKENS_DEFAULT)

    sorted_providers = sorted(PROVIDERS, key=lambda p: p.priority)
    last_error = None

    for provider in sorted_providers:
        try:
            return _try_provider(provider, messages, max_tokens)
        except Exception as exc:
            last_error = exc
            if _is_auth_error(exc):
                logger.warning(
                    "Provider %s failed (auth/fallback trigger): %s",
                    provider.name,
                    exc,
                )
            else:
                logger.warning(
                    "Provider %s failed (runtime error): %s",
                    provider.name,
                    exc,
                )
            continue

    raise RoutingError(
        f"All providers exhausted. Last error: {last_error}"
    )
