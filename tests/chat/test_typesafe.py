import json
from unittest.mock import Mock

import httpx

from apps.chat.application.use_cases import Message


def test_typesafe_key_selects_jev_and_preserves_context(monkeypatch):
    from apps.chat.infrastructure.classification import create_classifier

    monkeypatch.setenv("TYPESAFE_API_KEY", "fake-typesafe")
    messages = [Message("assistant", "Use sorted."), Message("user", "E ao contrário?")]
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            headers={"x-request-id": "req_typesafe_123"},
            json={
                "model": "jev-1.13.0",
                "answers": {
                    "python": {"type": "noul", "noul": 0.99},
                    "injection": {"type": "noul", "noul": 0.01},
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(
        "apps.chat.infrastructure.classification.httpx.Client", Mock(return_value=client)
    )
    result = create_classifier().classify(messages)

    assert (result.python_probability, result.injection_probability) == (0.99, 0.01)
    assert result.evaluator == "typesafe"
    assert result.model == "jev-1.13.0"
    assert result.request_id == "req_typesafe_123"
    assert isinstance(result.duration_ms, int)
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.typesafe.ai/v1/systemone"
    assert request.headers["Authorization"] == "Bearer fake-typesafe"
    body = json.loads(request.content)
    assert body["model"] == "jev-latest"
    assert body["state"] == [{"role": m.role, "content": m.content} for m in messages]
    assert set(body["questions"]) == {"python", "injection"}
