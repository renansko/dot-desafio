from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Document:
    id: str
    source: str
    text: str
    title: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    text: str
    offset: int
    title: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Match:
    id: str
    source: str
    snippet: str
    score: float
    title: str = ""
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class IndexSpec:
    provider: str
    model: str
    revision: str = ""
    chunk_size: int = 400
    chunk_overlap: int = 60
    splitter: str = "characters-v1"
    metric: str = "cosine"
    version: int = 1


class Embeddings(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SearchIndex(Protocol):
    def replace(self, chunks: list[Chunk], vectors: list[list[float]], spec: IndexSpec): ...

    def open(self, spec: IndexSpec): ...

    def rank(self, vector: list[float]) -> list[Match]: ...
