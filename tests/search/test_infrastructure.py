import json
import sys
import zipfile
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import openai
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.search.application.errors import InvalidCorpus, SearchTimeout, SearchUnavailable
from apps.search.infrastructure.corpus import read_corpus
from apps.search.infrastructure.embeddings import LangChainEmbeddings
from apps.search.infrastructure.faiss_index import FaissIndex
from apps.search.infrastructure.settings import LOCAL_MODEL, load_config
from tests.search.conftest import DeterministicEmbeddings


def test_local_config_independent_of_chat():
    config = load_config({"CHAT_PROVIDER": "invalid", "CHAT_MODEL": "invalid"})
    assert config.spec.provider == "local"
    assert config.spec.model == LOCAL_MODEL
    assert config.spec.chunk_size == 400


@pytest.mark.parametrize("name,value", [
    ("SEARCH_CHUNK_SIZE", "0"), ("SEARCH_CHUNK_SIZE", "2001"),
    ("SEARCH_CHUNK_OVERLAP", "-1"), ("SEARCH_CHUNK_OVERLAP", "400"),
    ("EMBEDDING_TIMEOUT_SECONDS", "0"), ("EMBEDDING_TIMEOUT_SECONDS", "301"),
    ("SEARCH_CHUNK_SIZE", "invalid"), ("EMBEDDING_PROVIDER", "unknown"),
    ("EMBEDDING_MODEL", " "),
])
def test_invalid_config(name, value):
    with pytest.raises(SearchUnavailable):
        load_config({name: value})


@pytest.mark.parametrize("size", [1, 2, 1999, 2000])
def test_chunk_size_config_boundaries(size):
    assert load_config({
        "SEARCH_CHUNK_SIZE": str(size), "SEARCH_CHUNK_OVERLAP": "0",
    }).spec.chunk_size == size


@pytest.mark.parametrize("overlap", [0, 1, 398, 399])
def test_overlap_config_boundaries(overlap):
    assert load_config({"SEARCH_CHUNK_OVERLAP": str(overlap)}).spec.chunk_overlap == overlap


@pytest.mark.parametrize("timeout", [1, 2, 299, 300])
def test_timeout_config_boundaries(timeout):
    assert load_config({"EMBEDDING_TIMEOUT_SECONDS": str(timeout)}).timeout == timeout


def test_openai_adapter_configuration(monkeypatch):
    factory = Mock()
    monkeypatch.setattr("apps.search.infrastructure.embeddings.OpenAIEmbeddings", factory)
    config = load_config({"EMBEDDING_PROVIDER": "openai", "OPENAI_API_KEY": "test-secret"})
    provider = LangChainEmbeddings(config)
    provider.embed_documents(["a"])
    provider.embed_query("q")
    factory.assert_called_once_with(
        model="text-embedding-3-small", api_key="test-secret", request_timeout=30,
        max_retries=0, check_embedding_ctx_length=False,
    )
    factory.return_value.embed_documents.assert_called_once_with(["a"])
    factory.return_value.embed_query.assert_called_once_with("q")
    assert "test-secret" not in repr(config)


def test_local_adapter_offline_and_revision(monkeypatch):
    factory = Mock()
    monkeypatch.setitem(sys.modules, "langchain_huggingface", SimpleNamespace(
        HuggingFaceEmbeddings=factory,
    ))
    provider = LangChainEmbeddings(load_config({"EMBEDDING_REVISION": "fixed-revision"}))
    provider.embed_query("q")
    factory.assert_called_once_with(
        model_name=LOCAL_MODEL,
        model_kwargs={"device": "cpu", "local_files_only": True, "revision": "fixed-revision"},
    )


def test_missing_openai_key():
    with pytest.raises(SearchUnavailable):
        LangChainEmbeddings(load_config({"EMBEDDING_PROVIDER": "openai"})).embed_query("q")


@pytest.mark.parametrize("error,expected", [
    (openai.APITimeoutError(request=httpx.Request("POST", "https://example.test")), SearchTimeout),
    (openai.APIConnectionError(request=httpx.Request("POST", "https://example.test")),
     SearchUnavailable),
    (OSError("model missing"), SearchUnavailable),
    (ImportError("extra not installed"), SearchUnavailable),
    (ValueError("invalid model"), SearchUnavailable),
])
def test_embedding_errors(error, expected):
    provider = LangChainEmbeddings(load_config({}))
    provider.__dict__["model"] = Mock(embed_query=Mock(side_effect=error))
    with pytest.raises(expected):
        provider.embed_query("q")


def test_corpus_nested_files_utf8_and_stable_ids(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.json").write_text(json.dumps({
        "identifier": "book:1", "source": "library", "title": "Livro",
        "text": "ação", "url": "https://example.test/book/1", "metadata": {"author": "Ana"},
    }), encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")
    docs = read_corpus(tmp_path)
    assert len(docs) == 1
    assert docs[0].id == "book:1"
    assert docs[0].source == "library"
    assert docs[0].text == "ação"
    assert docs[0].url == "https://example.test/book/1"
    assert docs[0].metadata == {"author": "Ana"}


def test_non_utf8_corpus(tmp_path):
    (tmp_path / "a.json").write_bytes(b"\xff")
    with pytest.raises(InvalidCorpus, match="UTF-8"):
        read_corpus(tmp_path)


def test_missing_corpus(tmp_path):
    with pytest.raises(InvalidCorpus, match="inexistente"):
        read_corpus(tmp_path / "missing")


def test_index_command_persists_and_reopens(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.search.management.commands.index_documents.LangChainEmbeddings",
        lambda config: DeterministicEmbeddings(),
    )
    output = StringIO()
    call_command("index_documents", stdout=output)
    assert "documentos" in output.getvalue() and "trechos indexados" in output.getvalue()
    config = load_config()
    assert len(FaissIndex(config.path).open(config.spec).rank([1, 0])) == 3


@pytest.mark.parametrize("empty_file", [False, True])
def test_command_empty_diagnostic(tmp_path, empty_file):
    if empty_file:
        (tmp_path / "empty.json").write_text(json.dumps({
            "identifier": "empty", "source": "test", "text": "  ",
        }))
    expected = "Documento vazio" if empty_file else "Corpus vazio"
    with pytest.raises(CommandError, match=expected):
        call_command("index_documents", corpus=str(tmp_path))


@pytest.mark.parametrize("error,message", [
    (SearchTimeout(), "Tempo limite"), (RuntimeError("secret"), "Falha na indexação"),
])
def test_command_safe_failure(monkeypatch, error, message):
    monkeypatch.setattr(
        "apps.search.management.commands.index_documents.LangChainEmbeddings",
        Mock(side_effect=error),
    )
    with pytest.raises(CommandError, match=message):
        call_command("index_documents")


def test_corrupt_archive(built_index):
    path, spec, _ = built_index
    path.write_bytes(b"broken")
    with pytest.raises(SearchUnavailable):
        FaissIndex(path).open(spec)


@pytest.mark.parametrize("change", ["hash", "dimension", "count", "invalid-json"])
def test_corrupt_metadata(built_index, change):
    path, spec, _ = built_index
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        payload = archive.read("vectors.faiss")
    updates = {"hash": {"sha256": "wrong"}, "dimension": {"dimension": 123},
               "count": {"chunks": []}, "invalid-json": {}}
    metadata.update(updates[change])
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("vectors.faiss", payload)
        archive.writestr("metadata.json", "{" if change == "invalid-json" else json.dumps(metadata))
    with pytest.raises(SearchUnavailable):
        FaissIndex(path).open(spec)
