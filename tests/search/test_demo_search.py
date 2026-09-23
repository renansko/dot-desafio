from types import SimpleNamespace

from scripts.demo_search import check_example, rebuild_index


class ExampleClient:
    def post(self, path, payload, format):
        assert path == "/api/search/"
        assert payload == {"query": "Como explicar modelos?", "k": 1}
        assert format == "json"
        return SimpleNamespace(
            status_code=200,
            data={
                "results": [
                    {
                        "id": "wikipedia:233488",
                        "title": "Machine learning",
                        "score": 0.72,
                        "url": "https://en.wikipedia.org/wiki/Machine_learning",
                        "snippet": "Explicação de modelos.",
                    }
                ]
            },
        )


def test_demo_uses_local_expected_id_for_local_embeddings(capsys):
    example = {
        "query": "Como explicar modelos?",
        "expected_id": "arxiv:2304.02381v2",
        "expected_id_local": "wikipedia:233488",
    }

    assert check_example(ExampleClient(), example, 1, "local") == 0
    assert "[OK]" in capsys.readouterr().out


def test_rebuild_index_reports_progress_before_and_after_work(capsys):
    events = []

    def command(name):
        events.append((name, capsys.readouterr().out))

    rebuild_index(command, "local", clock=iter([10.0, 12.345]).__next__)

    assert events == [("index_documents", "[2/3] Reconstruindo índice semântico (local)...\n")]
    assert capsys.readouterr().out == "      Índice pronto em 2.35s.\n"
