import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Rede proibida nos testes de chat")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
        "TYPESAFE_MODEL",
        "CHAT_MODEL",
        "CHAT_PROVIDER",
        "CHAT_TIMEOUT_SECONDS",
        "CHAT_MAX_OUTPUT_TOKENS",
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "CHAT_MAX_QUESTION_CHARS",
        "CHAT_MAX_MESSAGE_CHARS",
        "CHAT_MAX_HISTORY_MESSAGES",
        "CHAT_MAX_TOTAL_CHARS",
    ):
        monkeypatch.delenv(name, raising=False)
