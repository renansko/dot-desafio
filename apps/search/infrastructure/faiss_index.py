import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np

from apps.search.application.contracts import Chunk, Match
from apps.search.application.errors import SearchUnavailable


def normalized(vectors, rows):
    try:
        matrix = np.asarray(vectors, dtype="float32")
    except (ValueError, TypeError) as exc:
        raise SearchUnavailable("Vetores inválidos.") from exc
    if matrix.ndim != 2 or matrix.shape[0] != rows or matrix.shape[1] == 0:
        raise SearchUnavailable("Dimensões de embeddings inválidas.")
    return normalize_matrix(matrix)


def normalize_matrix(matrix):
    norms = np.linalg.norm(matrix, axis=1)
    if not np.isfinite(matrix).all() or not np.isfinite(norms).all() or (norms == 0).any():
        raise SearchUnavailable("Embeddings devem conter vetores finitos e não nulos.")
    return np.ascontiguousarray(matrix / norms[:, None])


def atomic_write(path, metadata, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            with zipfile.ZipFile(file, "w") as archive:
                archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
                archive.writestr("vectors.faiss", payload)
            file.flush()
            os.fsync(file.fileno())
        # One atomic publication point prevents readers from observing mixed generations.
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class FaissIndex:
    def __init__(self, path):
        self.path = Path(path)

    def replace(self, chunks, vectors, spec):
        matrix = normalized(vectors, len(chunks))
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        payload = faiss.serialize_index(index).tobytes()
        metadata = {
            "spec": asdict(spec), "dimension": index.d,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "chunks": [asdict(chunk) for chunk in chunks],
        }
        atomic_write(self.path, metadata, payload)

    def open(self, spec):
        try:
            with zipfile.ZipFile(self.path) as archive:
                metadata = json.loads(archive.read("metadata.json"))
                payload = archive.read("vectors.faiss")
            return decode_snapshot(metadata, payload, spec)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile) as exc:
            raise SearchUnavailable(
                "Índice ausente, corrompido ou incompatível; reconstrua."
            ) from exc


def decode_snapshot(metadata, payload, spec):
    if metadata["spec"] != asdict(spec):
        raise SearchUnavailable("Índice incompatível; reconstrua com a configuração atual.")
    if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
        raise SearchUnavailable("Índice corrompido; reconstrua.")
    index = faiss.deserialize_index(np.frombuffer(payload, dtype="uint8").copy())
    chunks = [Chunk(**chunk) for chunk in metadata["chunks"]]
    validate_snapshot(index, chunks, metadata)
    return FaissSnapshot(index, chunks)


def validate_snapshot(index, chunks, metadata):
    if not isinstance(index, faiss.IndexFlatIP) or index.d != metadata["dimension"]:
        raise SearchUnavailable("Formato do índice inválido.")
    if not chunks or index.ntotal != len(chunks):
        raise SearchUnavailable("Metadados do índice inconsistentes.")


class FaissSnapshot:
    def __init__(self, index, chunks):
        self.index, self.chunks = index, chunks

    def rank(self, vector):
        matrix = normalized([vector], 1)
        if matrix.shape[1] != self.index.d:
            raise SearchUnavailable("Dimensão da consulta incompatível; reconstrua.")
        scores, positions = self.index.search(matrix, self.index.ntotal)
        # Stable tie ordering follows corpus order, independent of FAISS tie behavior.
        ranked = sorted(zip(scores[0], positions[0]), key=lambda pair: (-pair[0], pair[1]))
        return [self.match(int(position), float(score)) for score, position in ranked]

    def match(self, position, score):
        chunk = self.chunks[position]
        return Match(
            chunk.id, chunk.source, chunk.text, score,
            chunk.title, chunk.url, chunk.metadata,
        )
