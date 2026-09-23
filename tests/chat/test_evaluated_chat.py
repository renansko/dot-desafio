from unittest.mock import Mock

import httpx
import pytest
from langchain_core.messages import AIMessage
from rest_framework.test import APIClient


@pytest.mark.parametrize("evaluator", ["openai", "anthropic", "typesafe"])
@pytest.mark.parametrize("risk,generated", [(0.01, True), (0.9, False)])
def test_http_evaluation_then_generation_at_external_boundaries(
    monkeypatch, evaluator, risk, generated
):
    provider = {"anthropic": "anthropic", "openai": "openai", "typesafe": "openai"}[evaluator]
    monkeypatch.setenv("CHAT_PROVIDER", provider)
    monkeypatch.setenv("CHAT_MODEL", "test-model")
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "fake")
    monkeypatch.setenv("TYPESAFE_API_KEY", "fake-typesafe" if evaluator == "typesafe" else " ")
    model = Mock()
    events = []

    def classify(*args):
        events.append("classify")
        return {"python_probability": 0.99, "injection_probability": risk}

    def generate(*args):
        events.append("generate")
        return AIMessage(content="Use sorted(itens, reverse=True).")

    model.invoke.side_effect = generate
    model.with_structured_output.return_value.invoke.side_effect = classify
    factory = {"anthropic": "ChatAnthropic", "openai": "ChatOpenAI"}[provider]
    monkeypatch.setattr(f"apps.chat.infrastructure.providers.{factory}", Mock(return_value=model))

    def respond(request):
        classify()
        return httpx.Response(
            200,
            json={
                "answers": {
                    "python": {"type": "noul", "noul": 0.99},
                    "injection": {"type": "noul", "noul": risk},
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(
        "apps.chat.infrastructure.classification.httpx.Client", Mock(return_value=client)
    )
    response = APIClient().post(
        "/api/chat/",
        {
            "question": "E ao contrário?",
            "history": [{"role": "user", "content": "Como ordeno uma lista em Python?"}],
        },
        format="json",
    )

    assert response.status_code == 200
    assert events == (["classify", "generate"] if generated else ["classify"])
    expected = {
        True: "Use sorted(itens, reverse=True).",
        False: "Posso ajudar com programação Python. Reformule sua pergunta nesse contexto.",
    }
    assert response.data == {"answer": expected[generated]}
    if evaluator == "typesafe":
        model.with_structured_output.assert_not_called()
