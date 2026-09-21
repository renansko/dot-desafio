from dataclasses import replace

import pytest

from apps.search.application.contracts import Document, IndexSpec
from apps.search.application.errors import InvalidCorpus, InvalidSearch, SearchUnavailable
from apps.search.application.use_cases import BuildIndex, Search, split_document, validate_query
from apps.search.infrastructure.faiss_index import FaissIndex


def test_persist_reopen_order_unique_and_fewer_results(built_index):
    path, spec, embeddings = built_index
    matches = Search(embeddings, FaissIndex(path), spec).execute("related query", 20)
    assert [match.id for match in matches] == ["a", "b"]
    assert matches[0].source == "a.txt"
    assert matches[0].snippet == "alpha alpha "
    assert [match.score for match in matches] == pytest.approx([1.0, 0.6])
    assert len(Search(embeddings, FaissIndex(path), spec).execute("query", 1)) == 1


@pytest.mark.parametrize("field,value", [
    ("provider", "openai"), ("model", "other-same-dimension"), ("revision", "abc"),
    ("chunk_size", 13), ("chunk_overlap", 1), ("version", 2),
    ("splitter", "other"), ("metric", "euclidean"),
])
def test_incompatible_spec_even_with_same_dimension(built_index, field, value):
    path, spec, embeddings = built_index
    with pytest.raises(SearchUnavailable, match="incompatível"):
        Search(embeddings, FaissIndex(path), replace(spec, **{field: value})).execute("q")


@pytest.mark.parametrize("length", [1999, 2000])
def test_query_length_allowed(length):
    validate_query("a" * length, 5)


@pytest.mark.parametrize("k", [1, 2, 19, 20])
def test_count_allowed(k):
    validate_query("q", k)


@pytest.mark.parametrize("query,k", [
    ("a" * 2001, 5), ("", 5), (" \n ", 5), (None, 5), (12, 5),
    ("q", 0), ("q", 21), ("q", -1), ("q", True), ("q", "1"), ("q", 1.5),
])
def test_invalid_query(query, k):
    with pytest.raises(InvalidSearch):
        validate_query(query, k)


@pytest.mark.parametrize("length,offsets", [(9, [0]), (10, [0]), (11, [0, 8])])
def test_chunk_boundaries(length, offsets):
    document = Document("id", "source", "x" * length)
    chunks = split_document(document, IndexSpec("local", "test", chunk_size=10, chunk_overlap=2))
    assert [chunk.offset for chunk in chunks] == offsets
    assert all(chunk.text == document.text[chunk.offset:chunk.offset + 10] for chunk in chunks)


def test_overlapping_chunks_preserve_source_and_text():
    chunks = split_document(
        Document("a", "a.txt", "abcdefghijklmnop"),
        IndexSpec("local", "test", chunk_size=10, chunk_overlap=2),
    )
    assert [chunk.text for chunk in chunks] == ["abcdefghij", "ijklmnop"]
    assert [(chunk.id, chunk.source) for chunk in chunks] == [("a", "a.txt")] * 2


@pytest.mark.parametrize("documents,diagnostic", [
    ([], "Corpus vazio"), ([Document("a", "empty.txt", " \n")], "Documento vazio: empty.txt"),
])
def test_empty_corpus_preserves_existing_index(built_index, documents, diagnostic):
    path, spec, embeddings = built_index
    before = path.read_bytes()
    with pytest.raises(InvalidCorpus, match=diagnostic):
        BuildIndex(embeddings, FaissIndex(path), spec).execute(documents)
    assert path.read_bytes() == before


@pytest.mark.parametrize("failure_point", ["embedding", "serialization", "publication"])
def test_failed_rebuild_preserves_previous_generation(built_index, monkeypatch, failure_point):
    path, spec, embeddings = built_index
    before = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("injected failure")

    with monkeypatch.context() as patch:
        targets = {
            "embedding": (embeddings, "embed_documents"),
            "serialization": ("apps.search.infrastructure.faiss_index.faiss.serialize_index",),
            "publication": ("apps.search.infrastructure.faiss_index.os.replace",),
        }
        patch.setattr(*targets[failure_point], fail)
        with pytest.raises(OSError):
            BuildIndex(embeddings, FaissIndex(path), spec).execute([Document("c", "c", "new")])
    assert path.read_bytes() == before
    assert len(list(path.parent.iterdir())) == 1
    assert Search(embeddings, FaissIndex(path), spec).execute("q")[0].id == "a"


def test_open_snapshot_survives_successful_rebuild(built_index):
    path, spec, embeddings = built_index
    snapshot = FaissIndex(path).open(spec)
    BuildIndex(embeddings, FaissIndex(path), spec).execute([Document("c", "c", "beta")])
    assert snapshot.rank([1, 0])[0].id == "a"
    assert Search(embeddings, FaissIndex(path), spec).execute("q")[0].id == "c"


def test_best_chunk_can_be_later_in_document_and_ties_are_stable(built_index):
    path, spec, embeddings = built_index
    docs = [Document("a", "a.txt", "beta beta   alpha"), Document("b", "b.txt", "alpha")]
    BuildIndex(embeddings, FaissIndex(path), spec).execute(docs)
    matches = Search(embeddings, FaissIndex(path), spec).execute("q")
    assert [match.id for match in matches] == ["a", "b"]
    assert matches[0].snippet == "alpha"
    assert matches[0].score == pytest.approx(1.0)


@pytest.mark.parametrize("vector", [[1], [0, 0], [float("nan"), 1], [float("inf"), 1]])
def test_invalid_query_embedding(built_index, vector):
    path, spec, _ = built_index
    with pytest.raises(SearchUnavailable):
        FaissIndex(path).open(spec).rank(vector)


@pytest.mark.parametrize("vectors", [[], [[0, 0]], [[1, float("nan")]], [[1], [1, 2]]])
def test_invalid_build_vectors_preserve_index(built_index, vectors):
    path, spec, _ = built_index
    before = path.read_bytes()
    chunks = split_document(Document("c", "c", "new"), spec)
    with pytest.raises(SearchUnavailable):
        FaissIndex(path).replace(chunks, vectors, spec)
    assert path.read_bytes() == before
