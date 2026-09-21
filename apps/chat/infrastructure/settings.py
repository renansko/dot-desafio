import os
from dataclasses import dataclass, field

from apps.chat.application.errors import ChatUnavailable
from apps.chat.application.use_cases import Limits


@dataclass(frozen=True)
class ChatConfig:
    provider: str
    model: str
    api_key: str = field(repr=False)
    timeout: int = 30
    max_tokens: int = 1024
    tracing: bool = False


def positive_integer(env, name, default):
    try:
        value = int(env.get(name, default))
    except (ValueError, TypeError):
        raise ChatUnavailable() from None
    if value <= 0:
        raise ChatUnavailable()
    return value


def load_limits(env=None):
    env = os.environ if env is None else env
    return Limits(
        question=positive_integer(env, "CHAT_MAX_QUESTION_CHARS", 4000),
        message=positive_integer(env, "CHAT_MAX_MESSAGE_CHARS", 4000),
        history=positive_integer(env, "CHAT_MAX_HISTORY_MESSAGES", 20),
        total=positive_integer(env, "CHAT_MAX_TOTAL_CHARS", 16000),
    )


def load_config(env=None):
    env = os.environ if env is None else env
    provider = env.get("CHAT_PROVIDER", "openai").strip().lower()
    keys = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
    if provider not in keys:
        raise ChatUnavailable()
    key = env.get(keys[provider], "").strip()
    model = env.get("CHAT_MODEL", "").strip()
    if not key or not model:
        raise ChatUnavailable()
    return ChatConfig(
        provider,
        model,
        key,
        timeout=positive_integer(env, "CHAT_TIMEOUT_SECONDS", 30),
        max_tokens=positive_integer(env, "CHAT_MAX_OUTPUT_TOKENS", 1024),
        tracing=tracing_enabled(env),
    )


def tracing_enabled(env):
    value = env.get("LANGSMITH_TRACING", "false").lower()
    if value not in ("true", "false"):
        raise ChatUnavailable()
    if value == "true" and not env.get("LANGSMITH_API_KEY", "").strip():
        raise ChatUnavailable()
    return value == "true"
