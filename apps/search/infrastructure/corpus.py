import json
from pathlib import Path

from apps.search.application.contracts import Document
from apps.search.application.errors import InvalidCorpus


def read_corpus(directory):
    root = Path(directory)
    if not root.is_dir():
        raise InvalidCorpus("Diretório do corpus inexistente.")
    try:
        return [
            document_from_json(path)
            for path in sorted(root.rglob("*.json")) if path.is_file()
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InvalidCorpus("Corpus ilegível: use documentos JSON UTF-8 válidos.") from exc


def document_from_json(path):
    payload = json.loads(path.read_text("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Documento JSON deve ser objeto.")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("Metadados devem ser objeto.")
    identifier = payload.get("identifier")
    source = payload.get("source")
    text = payload.get("text")
    valid_ids = isinstance(identifier, str) and identifier.strip()
    valid_source = isinstance(source, str) and source.strip()
    if not (valid_ids and valid_source and isinstance(text, str)):
        raise ValueError("Documento exige identifier e source não vazios e text string.")
    return Document(
        id=identifier, source=source, text=text,
        title=payload.get("title", ""), url=payload.get("url", ""), metadata=metadata,
    )
