import json
from unittest.mock import Mock

from apps.chat.application.use_cases import AskPython, Assessment


def test_decision_log_identifies_jev_without_conversation_content(monkeypatch):
    logger = Mock()
    monkeypatch.setattr("apps.chat.application.use_cases.decision_logger", logger)
    provider, classifier = Mock(), Mock()
    classifier.classify.return_value = Assessment(
        python_probability=0.31,
        injection_probability=0.02,
        evaluator="typesafe",
        model="jev-1.13.0",
        request_id="req_123",
        duration_ms=42,
    )
    secret_question = "Minha pergunta privada"

    AskPython(provider, classifier=classifier).execute(secret_question, [])

    event = json.loads(logger.info.call_args.args[0])
    assert event == {
        "event": "chat_assessment",
        "evaluator": "typesafe",
        "model": "jev-1.13.0",
        "request_id": "req_123",
        "python_probability": 0.31,
        "injection_probability": 0.02,
        "python_threshold": 0.85,
        "injection_threshold": 0.15,
        "decision": "reject_scope",
        "duration_ms": 42,
    }
    assert secret_question not in logger.info.call_args.args[0]
    provider.answer.assert_not_called()


def test_decision_log_distinguishes_injection_and_generation(monkeypatch):
    logger = Mock()
    monkeypatch.setattr("apps.chat.application.use_cases.decision_logger", logger)
    provider, classifier = Mock(), Mock()
    provider.answer.return_value = "Resposta"
    assessments = [
        Assessment(0.99, 0.15, "openai", "test-model", None, 7),
        Assessment(0.85, 0.149, "openai", "test-model", "req_456", 8),
    ]
    classifier.classify.side_effect = assessments

    AskPython(provider, classifier=classifier).execute("Python?", [])
    AskPython(provider, classifier=classifier).execute("Python?", [])

    decisions = [json.loads(call.args[0])["decision"] for call in logger.info.call_args_list]
    assert decisions == ["reject_injection", "generate"]
