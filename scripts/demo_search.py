"""Demonstração real, separada de pytest: python -m scripts.demo_search."""

import json
import os
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import call_command
    from rest_framework.test import APIClient

    # Exercise the real command and HTTP stack without requiring a separate server.
    call_command("index_documents")
    examples = json.loads(Path("apps/brain/expected.json").read_text("utf-8"))
    failures = 0
    for example in examples:
        failures += check_example(APIClient(), example)
    if failures:
        raise SystemExit(f"Demonstração: {failures} consultas divergiram do esperado.")
    print(f"Demonstração concluída: {len(examples)}/{len(examples)} resultados esperados.")


def check_example(client, example):
    response = client.post("/api/search/", {"query": example["query"], "k": 1}, format="json")
    if response.status_code != 200:
        raise SystemExit(f"Busca falhou: HTTP {response.status_code}: {response.data}")
    match = response.data["results"][0]
    print(f"{example['query']} -> {match['id']} (score={match['score']:.4f})")
    return int(match["id"] != example["expected_id"])


if __name__ == "__main__":
    main()
