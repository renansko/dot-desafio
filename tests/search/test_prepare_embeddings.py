from types import SimpleNamespace

from scripts import prepare_embeddings


def test_prepare_embeddings_reports_model_and_elapsed_time_before_loading(monkeypatch, capsys):
    events = []

    class FakeSentenceTransformer:
        def __init__(self, model, revision, device):
            events.append((model, revision, device, capsys.readouterr().out))

    monkeypatch.setattr(
        prepare_embeddings,
        "load_config",
        lambda: SimpleNamespace(
            spec=SimpleNamespace(provider="local", model="test/model", revision="rev-1")
        ),
    )
    monkeypatch.setattr(
        prepare_embeddings,
        "load_sentence_transformer",
        lambda: FakeSentenceTransformer,
    )

    prepare_embeddings.main(clock=iter([20.0, 23.21]).__next__)

    assert events == [("test/model", "rev-1", "cpu", '[1/1] Preparando modelo "test/model"...\n')]
    assert capsys.readouterr().out == ("      Modelo disponível no cache Hugging Face em 3.21s.\n")
