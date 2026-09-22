from unittest.mock import Mock

import anthropic
import httpx
import openai
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_openai.chat_models.base import OpenAIRefusalError

from apps.chat.application.errors import ChatTimeout, ChatUnavailable
from apps.chat.application.use_cases import Message
from apps.chat.infrastructure.classification import create_classifier


@pytest.mark.parametrize(
    "error",
    [
        OpenAIRefusalError("secret"),
        openai.LengthFinishReasonError(completion=Mock()),
        openai.ContentFilterFinishReasonError(),
    ],
)
def test_openai_refusal_or_incomplete_output_is_unavailable(monkeypatch, error):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("CHAT_MODEL", "test-model")
    model = Mock()
    model.with_structured_output.return_value.invoke.side_effect = error
    monkeypatch.setattr("apps.chat.infrastructure.providers.ChatOpenAI", Mock(return_value=model))
    with pytest.raises(ChatUnavailable):
        create_classifier().classify([Message("user", "Python?")])


@pytest.mark.parametrize(
    "provider,sdk,factory",
    [("openai", openai, "ChatOpenAI"), ("anthropic", anthropic, "ChatAnthropic")],
)
@pytest.mark.parametrize("kind", ["timeout", "connection", "auth", "parse", "refusal"])
def test_structured_failure_is_a_dependency_error(monkeypatch, provider, sdk, factory, kind):
    monkeypatch.setenv("CHAT_PROVIDER", provider)
    monkeypatch.setenv("CHAT_MODEL", "test-model")
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "fake")
    request = httpx.Request("POST", "https://example.test")
    errors = {
        "timeout": sdk.APITimeoutError(request=request),
        "connection": sdk.APIConnectionError(request=request),
        "auth": sdk.APIStatusError(
            "secret", response=httpx.Response(401, request=request), body=None
        ),
        "parse": OutputParserException("secret"),
        "refusal": ValueError("secret"),
    }
    model = Mock()
    model.with_structured_output.return_value.invoke.side_effect = errors[kind]
    monkeypatch.setattr(f"apps.chat.infrastructure.providers.{factory}", Mock(return_value=model))
    with pytest.raises(ChatTimeout if kind == "timeout" else ChatUnavailable):
        create_classifier().classify([Message("user", "Python?")])


@pytest.mark.parametrize(
    "kind",
    [
        "timeout",
        "connection",
        "auth",
        "rate",
        "server",
        "json",
        "missing",
        "wrong_type",
        "invalid_score",
    ],
)
def test_typesafe_failure_does_not_fall_back(monkeypatch, kind):
    monkeypatch.setenv("TYPESAFE_API_KEY", "fake-typesafe")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("CHAT_MODEL", "test-model")
    fallback = Mock()
    monkeypatch.setattr("apps.chat.infrastructure.providers.ChatOpenAI", fallback)

    def respond(request):
        if kind in ("timeout", "connection"):
            error = httpx.ReadTimeout if kind == "timeout" else httpx.ConnectError
            raise error("secret", request=request)
        if kind in ("auth", "rate", "server"):
            return httpx.Response({"auth": 401, "rate": 429, "server": 503}[kind])
        payloads = {
            "json": b"not json",
            "missing": b'{"answers": {}}',
            "wrong_type": b'{"answers": []}',
            "invalid_score": b'{"answers": {"python": {"type": "noul", "noul": 2}, '
            b'"injection": {"type": "noul", "noul": 0}}}',
        }
        return httpx.Response(200, content=payloads[kind])

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(
        "apps.chat.infrastructure.classification.httpx.Client", Mock(return_value=client)
    )
    with pytest.raises(ChatTimeout if kind == "timeout" else ChatUnavailable):
        create_classifier().classify([Message("user", "Python?")])
    fallback.assert_not_called()
