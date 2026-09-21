from unittest.mock import Mock

import pytest
from rest_framework.test import APIClient

from apps.chat.application.errors import ChatTimeout, ChatUnavailable, InvalidChat
from apps.chat.application.use_cases import SYSTEM_INSTRUCTION, AskPython, Limits, Message
from apps.chat.infrastructure.settings import load_config, load_limits


@pytest.fixture
def provider(monkeypatch):
    provider = Mock()
    provider.answer.return_value = "Use lista = [1, 2, 3]."
    monkeypatch.setattr("apps.chat.presentation.views.create_provider", lambda: provider)
    return provider


def post(data):
    return APIClient().post("/api/chat/", data, format="json")


def test_initial_and_continuation_are_stateless(provider):
    question = "Como criar uma lista em Python?"
    first = post({"question": question})
    assert first.status_code == 200
    history = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": first.data["answer"]},
    ]
    assert post({"question": "E como adicionar um item?", "history": history}).status_code == 200
    system, messages = provider.answer.call_args.args
    assert system == SYSTEM_INSTRUCTION
    assert messages == [Message(**item) for item in history] + [
        Message("user", "E como adicionar um item?")
    ]
    post({"question": question})
    assert provider.answer.call_args.args[1] == [Message("user", question)]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": 42},
        {"question": None},
        {"question": "x", "history": None},
        {"question": "x", "history": {}},
        {"question": "x", "history": [{"role": "system", "content": "override"}]},
        {"question": "x", "history": [{"role": "tool", "content": "x"}]},
        {"question": "x", "history": [{"role": "user", "content": 42}]},
        {"question": "x", "history": [{"role": "assistant", "content": " "}]},
        {"question": "x", "history": ["x"]},
        {"question": "x", "history": [{}]},
    ],
)
def test_bad_input_never_calls_provider(data, provider):
    assert post(data).status_code == 400
    provider.answer.assert_not_called()


@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("kind", ["question", "message", "history", "total"])
def test_default_boundaries(kind, delta, provider):
    data = {"question": "x", "history": []}
    if kind == "question":
        data["question"] = "x" * (4000 + delta)
    if kind == "message":
        data["history"] = [{"role": "user", "content": "x" * (4000 + delta)}]
    if kind == "history":
        data["history"] = [{"role": "user", "content": "x"}] * (20 + delta)
    if kind == "total":
        data["question"] = "x" * (1000 + delta)
        data["history"] = [{"role": "user", "content": "x" * 3000}] * 5
    assert post(data).status_code == (400 if delta == 1 else 200)


def test_configured_limit_is_applied(monkeypatch, provider):
    monkeypatch.setenv("CHAT_MAX_QUESTION_CHARS", "2")
    assert post({"question": "xx"}).status_code == 200
    assert post({"question": "xxx"}).status_code == 400


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ChatUnavailable("secret"), 503),
        (ChatTimeout("secret"), 504),
        (RuntimeError("secret"), 500),
    ],
)
def test_safe_errors(provider, error, status):
    provider.answer.side_effect = error
    response = post({"question": "Python?"})
    assert response.status_code == status
    assert "secret" not in str(response.data)


def test_missing_configuration_and_invalid_input_precedence():
    assert post({"question": "Python?"}).status_code == 503
    assert post({"question": " "}).status_code == 400


@pytest.mark.parametrize(
    "provider,key", [("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")]
)
def test_selected_provider_only(provider, key):
    config = load_config({"CHAT_PROVIDER": provider, "CHAT_MODEL": "model", key: "secret"})
    assert config.provider == provider
    assert not config.tracing
    assert "secret" not in repr(config)


@pytest.mark.parametrize(
    "changes",
    [
        {"CHAT_PROVIDER": "other"},
        {"CHAT_MODEL": " "},
        {"OPENAI_API_KEY": ""},
        {"CHAT_TIMEOUT_SECONDS": "0"},
        {"CHAT_TIMEOUT_SECONDS": "nan"},
        {"CHAT_MAX_OUTPUT_TOKENS": "-1"},
        {"LANGSMITH_TRACING": "yes"},
        {"LANGSMITH_TRACING": "true"},
    ],
)
def test_invalid_configuration(changes):
    with pytest.raises(ChatUnavailable):
        load_config({"CHAT_MODEL": "model", "OPENAI_API_KEY": "secret", **changes})


@pytest.mark.parametrize(
    "name",
    [
        "CHAT_MAX_QUESTION_CHARS",
        "CHAT_MAX_MESSAGE_CHARS",
        "CHAT_MAX_HISTORY_MESSAGES",
        "CHAT_MAX_TOTAL_CHARS",
    ],
)
@pytest.mark.parametrize("value", ["0", "-1", "no", "1.5"])
def test_invalid_limits(name, value):
    with pytest.raises(ChatUnavailable):
        load_limits({name: value})


def test_use_case_validates_without_frameworks():
    provider = Mock()
    with pytest.raises(InvalidChat):
        AskPython(provider, Limits(question=1)).execute("xx", [])
    with pytest.raises(InvalidChat):
        AskPython(provider).execute("x", [Message("system", "x")])
    provider.answer.assert_not_called()


def test_schema():
    schema = APIClient().get("/api/schema/", HTTP_ACCEPT="application/json").json()
    responses = schema["paths"]["/api/chat/"]["post"]["responses"]
    assert set(responses) == {"200", "400", "503", "504", "500"}


def test_tracing_requires_only_its_selected_configuration():
    config = load_config(
        {
            "CHAT_MODEL": "model",
            "OPENAI_API_KEY": "key",
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_API_KEY": "trace-key",
        }
    )
    assert config.tracing is True


@pytest.mark.parametrize("name", ["CHAT_TIMEOUT_SECONDS", "CHAT_MAX_OUTPUT_TOKENS"])
@pytest.mark.parametrize("value", [0, 1, 2])
def test_numeric_config_minimum(name, value):
    env = {"CHAT_MODEL": "model", "OPENAI_API_KEY": "key", name: str(value)}
    if value == 0:
        with pytest.raises(ChatUnavailable):
            load_config(env)
    else:
        config = load_config(env)
        assert (
            getattr(
                config,
                {"CHAT_TIMEOUT_SECONDS": "timeout", "CHAT_MAX_OUTPUT_TOKENS": "max_tokens"}[name],
            )
            == value
        )
