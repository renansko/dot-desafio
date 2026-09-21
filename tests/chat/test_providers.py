from unittest.mock import Mock

import anthropic
import httpx
import openai
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith.run_helpers import get_tracing_context

from apps.chat.application.errors import ChatTimeout, ChatUnavailable
from apps.chat.application.use_cases import Message
from apps.chat.infrastructure.providers import LangChainChat, create_provider, response_text
from apps.chat.infrastructure.settings import ChatConfig


@pytest.fixture(
    params=[("openai", "ChatOpenAI", openai), ("anthropic", "ChatAnthropic", anthropic)]
)
def adapter(request, monkeypatch):
    provider, factory_name, sdk = request.param
    model = Mock()
    model.invoke.return_value = AIMessage(content="Resposta")
    factory = Mock(return_value=model)
    monkeypatch.setattr(f"apps.chat.infrastructure.providers.{factory_name}", factory)
    monkeypatch.setenv("CHAT_PROVIDER", provider)
    monkeypatch.setenv("CHAT_MODEL", "test-model")
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "secret")
    return create_provider(), factory, model, sdk


def test_provider_construction_messages_and_tracing(adapter, monkeypatch):
    provider, factory, model, _ = adapter
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    def invoke(messages):
        assert get_tracing_context()["enabled"] is False
        return AIMessage(content="Resposta")

    model.invoke.side_effect = invoke
    assert (
        provider.answer("system", [Message("assistant", "anterior"), Message("user", "pergunta")])
        == "Resposta"
    )
    factory.assert_called_once_with(
        model="test-model", api_key="secret", timeout=30, max_tokens=1024, max_retries=0
    )
    assert model.invoke.call_args.args[0] == [
        SystemMessage(content="system"),
        AIMessage(content="anterior"),
        HumanMessage(content="pergunta"),
    ]


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_sdk_status_errors(adapter, status):
    provider, _, model, sdk = adapter
    response = httpx.Response(status, request=httpx.Request("POST", "https://example.test"))
    model.invoke.side_effect = sdk.APIStatusError("secret", response=response, body=None)
    with pytest.raises(ChatUnavailable):
        provider.answer("system", [Message("user", "x")])


def test_timeout_and_connection(adapter):
    provider, _, model, sdk = adapter
    request = httpx.Request("POST", "https://example.test")
    model.invoke.side_effect = sdk.APITimeoutError(request=request)
    with pytest.raises(ChatTimeout):
        provider.answer("system", [])
    model.invoke.side_effect = sdk.APIConnectionError(request=request)
    with pytest.raises(ChatUnavailable):
        provider.answer("system", [])


def test_unexpected_error_is_not_reclassified(adapter):
    provider, _, model, _ = adapter
    model.invoke.side_effect = RuntimeError("internal")
    with pytest.raises(RuntimeError):
        provider.answer("system", [])


@pytest.mark.parametrize("content", ["", " ", [], [{"type": "thinking", "thinking": "x"}]])
def test_no_text_is_unavailable(content):
    with pytest.raises(ChatUnavailable):
        response_text(content)


def test_text_blocks():
    assert response_text([{"type": "text", "text": "Olá"}, " mundo"]) == "Olá mundo"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_real_langchain_constructor_offline(provider):
    model = LangChainChat(ChatConfig(provider, "test-model", "fake-key")).build_model()
    assert model.max_retries == 0


def test_invalid_model_configuration(adapter):
    provider, factory, _, _ = adapter
    factory.side_effect = ValueError("internal config")
    with pytest.raises(ChatUnavailable):
        provider.answer("system", [])
