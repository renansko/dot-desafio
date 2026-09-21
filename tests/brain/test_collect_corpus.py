import json
from pathlib import Path

import pytest

from apps.brain.collect_corpus import (
    CollectionError,
    CorpusDocument,
    arxiv_documents,
    new_documents,
    save_documents,
    wikipedia_documents,
)


class FakeResponse:
    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body.encode()


def test_collects_wikipedia_content_with_citation_metadata():
    responses = iter(
        [
            json.dumps({"query": {"search": [{"pageid": 49038, "title": "Machine learning"}]}}),
            "<html><body><p>Machines learn from data.</p></body></html>",
        ]
    )

    documents = wikipedia_documents(
        "machine learning", 1, sleep_seconds=0, opener=lambda *_args, **_kwargs: FakeResponse(next(responses))
    )

    assert documents[0].title == "Machine learning"
    assert documents[0].text == "Machines learn from data."
    assert documents[0].url == "https://en.wikipedia.org/wiki/Machine_learning"
    assert documents[0].metadata["license"] == "CC BY-SA 4.0"
    assert documents[0].metadata["page_id"] == 49038


def test_collects_arxiv_abstract_and_metadata():
    feed = """<feed xmlns=\"http://www.w3.org/2005/Atom\"><entry>
      <id>http://arxiv.org/abs/1234.5678v1</id><title> Useful paper </title>
      <summary> A useful abstract. </summary><published>2026-01-01T00:00:00Z</published>
      <updated>2026-01-02T00:00:00Z</updated><author><name>Ada</name></author>
      <category term=\"cs.AI\" /></entry></feed>"""

    documents = arxiv_documents("artificial intelligence", 1, opener=lambda *_args, **_kwargs: FakeResponse(feed))

    assert documents[0].identifier == "arxiv:1234.5678v1"
    assert documents[0].text == "A useful abstract."
    assert documents[0].metadata["authors"] == ["Ada"]
    assert documents[0].metadata["categories"] == ["cs.AI"]


def test_saves_one_json_document_per_record(tmp_path: Path):
    documents = arxiv_documents(
        "test",
        1,
        opener=lambda *_args, **_kwargs: FakeResponse(
            "<feed xmlns=\"http://www.w3.org/2005/Atom\"><entry><id>http://arxiv.org/abs/1</id>"
            "<title>T</title><summary>Text</summary></entry></feed>"
        ),
    )

    paths = save_documents(documents, tmp_path)

    assert len(paths) == 1
    assert json.loads(paths[0].read_text(encoding="utf-8"))["source"] == "arxiv"


def test_explains_when_a_source_is_unavailable():
    def unavailable(*_args, **_kwargs):
        raise OSError("offline")

    with pytest.raises(CollectionError, match="Não foi possível coletar"):
        wikipedia_documents("machine learning", 1, sleep_seconds=0, opener=unavailable)


def test_removes_urls_already_stored_or_repeated_in_the_batch():
    first = CorpusDocument("one", "test", "One", "Text", "https://example.com/one", {})
    duplicate = CorpusDocument("two", "test", "Two", "Text", "https://example.com/one", {})
    new = CorpusDocument("three", "test", "Three", "Text", "https://example.com/three", {})

    documents = new_documents([first, duplicate, new], {"https://example.com/stored"})

    assert documents == [first, new]
