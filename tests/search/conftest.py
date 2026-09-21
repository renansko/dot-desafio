import socket

import pytest

from apps.search.application.contracts import Document, IndexSpec
from apps.search.application.use_cases import BuildIndex
from apps.search.infrastructure.faiss_index import FaissIndex


class DeterministicEmbeddings:
    def embed_documents(self, texts):
        return [[1.0, 0.0] if "alpha" in text else [0.6, 0.8] for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    def blocked(*args, **kwargs):
        raise AssertionError("Rede proibida nos testes de busca")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(tmp_path / "default.zip"))
    for name in (
        "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_REVISION",
        "EMBEDDING_TIMEOUT_SECONDS", "SEARCH_CHUNK_SIZE", "SEARCH_CHUNK_OVERLAP",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def built_index(tmp_path):
    spec = IndexSpec("local", "deterministic", chunk_size=12, chunk_overlap=0)
    embeddings = DeterministicEmbeddings()
    path = tmp_path / "search.zip"
    index = FaissIndex(path)
    docs = [Document("a", "a.txt", "alpha alpha alpha"), Document("b", "b.txt", "beta")]
    BuildIndex(embeddings, index, spec).execute(docs)
    return path, spec, embeddings
