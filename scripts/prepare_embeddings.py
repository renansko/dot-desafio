"""Download explícito do modelo local: python -m scripts.prepare_embeddings."""

from apps.search.infrastructure.settings import load_config


def main():
    from sentence_transformers import SentenceTransformer

    config = load_config()
    if config.spec.provider != "local":
        raise SystemExit("Preparação de download é exclusiva do provedor local.")
    revision = config.spec.revision or None
    SentenceTransformer(config.spec.model, revision=revision, device="cpu")
    print(f"Modelo preparado no cache Hugging Face: {config.spec.model}")


if __name__ == "__main__":
    main()
