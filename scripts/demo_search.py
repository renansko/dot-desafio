"""Demonstração real, separada de pytest: python -m scripts.demo_search."""

import json
import os
import time
from pathlib import Path


def main():
    print("[1/3] Inicializando Django e carregando configuração...", flush=True)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import call_command
    from rest_framework.test import APIClient

    from apps.search.infrastructure.settings import load_config

    # Reindexa e exercita o comando real e a camada HTTP da API
    provider = load_config().spec.provider
    rebuild_index(call_command, provider)
    examples = json.loads(Path("apps/brain/expected.json").read_text("utf-8"))
    failures = 0
    client = APIClient()
    print(f"[3/3] Validando {len(examples)} consultas pela API...", flush=True)
    print("\n--- INÍCIO DA DEMONSTRAÇÃO DA BUSCA SEMÂNTICA ---", flush=True)
    for index, example in enumerate(examples, start=1):
        failures += check_example(client, example, index, provider)
    if failures:
        raise SystemExit(f"Demonstração: {failures} consultas divergiram do esperado.")
    total = len(examples)
    print(f"\nDemonstração concluída com sucesso: {total}/{total} resultados esperados.")


def rebuild_index(call_command, provider, clock=time.perf_counter):
    print(f"[2/3] Reconstruindo índice semântico ({provider})...", flush=True)
    started = clock()
    call_command("index_documents")
    elapsed = clock() - started
    print(f"      Índice pronto em {elapsed:.2f}s.", flush=True)


def check_example(client, example, index, provider):
    response = client.post("/api/search/", {"query": example["query"], "k": 1}, format="json")
    if response.status_code != 200:
        raise SystemExit(f"Busca falhou: HTTP {response.status_code}: {response.data}")
    match = response.data["results"][0]
    expected_id = example.get(f"expected_id_{provider}", example["expected_id"])
    matched = match["id"] == expected_id
    status = "OK" if matched else "DIVERGÊNCIA"
    snippet_preview = " ".join(match["snippet"].split())[:120]
    print(f'\n[{index}] Consulta: "{example["query"]}"')
    print(f"    Resultado [{status}]: {match['title']} ({match['id']})")
    print(f"    Similaridade (score): {match['score']:.4f} | URL: {match['url']}")
    print(f'    Trecho: "{snippet_preview}..."')
    return int(not matched)


if __name__ == "__main__":
    main()
