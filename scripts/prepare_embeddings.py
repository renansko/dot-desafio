"""Download explícito do modelo local: python -m scripts.prepare_embeddings."""

import os
import time

from apps.search.infrastructure.settings import load_config


def load_sentence_transformer():
    # CI and terminals mounted through WSL render tqdm updates as many blank lines.
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer


def main(clock=time.perf_counter):
    config = load_config()
    if config.spec.provider != "local":
        raise SystemExit("Preparação de download é exclusiva do provedor local.")
    revision = config.spec.revision or None
    print(f'[1/1] Preparando modelo "{config.spec.model}"...', flush=True)
    started = clock()
    load_sentence_transformer()(config.spec.model, revision=revision, device="cpu")
    elapsed = clock() - started
    print(f"      Modelo disponível no cache Hugging Face em {elapsed:.2f}s.", flush=True)


if __name__ == "__main__":
    main()
