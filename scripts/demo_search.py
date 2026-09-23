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

    # Reindexa e exercita o comando real e a camada HTTP da API
    call_command("index_documents")
    examples = json.loads(Path("apps/brain/expected.json").read_text("utf-8"))
    failures = 0
    client = APIClient()
    print("\n--- INÍCIO DA DEMONSTRAÇÃO DA BUSCA SEMÂNTICA ---")
    for index, example in enumerate(examples, start=1):
        failures += check_example(client, example, index)
    if failures:
        raise SystemExit(f"Demonstração: {failures} consultas divergiram do esperado.")
    total = len(examples)
    print(f"\nDemonstração concluída com sucesso: {total}/{total} resultados esperados.")


def check_example(client, example, index):
    response = client.post("/api/search/", {"query": example["query"], "k": 1}, format="json")
    if response.status_code != 200:
        raise SystemExit(f"Busca falhou: HTTP {response.status_code}: {response.data}")
    match = response.data["results"][0]
    matched = match["id"] == example["expected_id"]
    status = "OK" if matched else "DIVERGÊNCIA"
    snippet_preview = " ".join(match["snippet"].split())[:120]
    print(f"\n[{index}] Consulta: \"{example['query']}\"")
    print(f"    Resultado [{status}]: {match['title']} ({match['id']})")
    print(f"    Similaridade (score): {match['score']:.4f} | URL: {match['url']}")
    print(f"    Trecho: \"{snippet_preview}...\"")
    return int(not matched)


if __name__ == "__main__":
    main()
