import os
from dataclasses import dataclass, field
from pathlib import Path

from apps.search.application.contracts import IndexSpec
from apps.search.application.errors import SearchUnavailable

LOCAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class SearchConfig:
    spec: IndexSpec
    path: Path
    api_key: str = field(default="", repr=False)
    timeout: int = 30


def integer(env, name, default, minimum, maximum):
    try:
        value = int(env.get(name, default))
    except (ValueError, TypeError) as exc:
        raise SearchUnavailable("Configuração numérica inválida.") from exc
    if not minimum <= value <= maximum:
        raise SearchUnavailable(f"{name} fora dos limites.")
    return value


def load_config(env=None):
    env = os.environ if env is None else env
    provider = env.get("EMBEDDING_PROVIDER", "local").strip().lower()
    if provider not in ("local", "openai"):
        raise SearchUnavailable("Provedor de embeddings inválido.")
    default = LOCAL_MODEL if provider == "local" else "text-embedding-3-small"
    model = env.get("EMBEDDING_MODEL", default).strip()
    if not model:
        raise SearchUnavailable("Modelo de embeddings vazio.")
    size = integer(env, "SEARCH_CHUNK_SIZE", 400, 1, 2000)
    spec = IndexSpec(
        provider=provider, model=model, revision=env.get("EMBEDDING_REVISION", ""),
        chunk_size=size,
        chunk_overlap=integer(env, "SEARCH_CHUNK_OVERLAP", 60, 0, size - 1),
    )
    return SearchConfig(
        spec=spec, path=Path(env.get("SEARCH_INDEX_PATH", "var/search/index.zip")),
        api_key=env.get("OPENAI_API_KEY", "").strip(),
        timeout=integer(env, "EMBEDDING_TIMEOUT_SECONDS", 30, 1, 300),
    )
