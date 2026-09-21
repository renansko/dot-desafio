# dot-desafio

Desafio Backend IA organizado em três entregas: biblioteca, chatbot e busca semântica. Fonte: `Prova - Backend IA.pdf`.

**Estado:** Q1 (biblioteca), Q2 (chatbot) e Q3 (busca semântica) implementadas.
Demonstração real da Q2 pendente de credencial OpenAI.

Stack: Python, Django + Django REST Framework, SQLite, LangChain e FAISS. Uma aplicação com Clean Architecture enxuta e contextos separados por módulo.

- [Chatbot: contrato, configuração e demonstração real](docs/modules/chat/CONTEXT.md)
- [Busca semântica: preparação, indexação e demonstração](docs/modules/search/CONTEXT.md)
- [Mapa dos módulos](CONTEXT-MAP.md)
- [Decisão de arquitetura](docs/adr/0001-arquitetura-do-desafio.md)
- [Convenções para agentes](AGENTS.md)
- [Issues de implementação](https://github.com/renansko/dot-desafio/issues)

| Issue | Entrega | Bloqueada por |
| --- | --- | --- |
| [Q1 — Biblioteca](https://github.com/renansko/dot-desafio/issues/1) | API de livros e base compartilhada | Nenhuma |
| [Q2 — Chatbot](https://github.com/renansko/dot-desafio/issues/2) | LangChain com OpenAI/Claude | Q1 |
| [Q3 — Busca semântica](https://github.com/renansko/dot-desafio/issues/3) | Embeddings e FAISS | Q1 |

## Organização

Os módulos ficam em `apps/`: `library/` (biblioteca), `chat/` (chatbot), `search/` (busca) e
`apps/brain/` (coleta e corpus). Configuração Django fica em `config/`; testes,
documentação e scripts de demonstração ficam em `tests/`, `docs/` e `scripts/`.

## Preparação e execução

Requer Python 3.12 ou superior. Nenhuma credencial é necessária para a biblioteca.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python manage.py migrate
python manage.py runserver
```

A documentação OpenAPI fica em `http://127.0.0.1:8000/api/docs/` e o schema em
`/api/schema/`.

```bash
# cadastrar
curl -X POST http://127.0.0.1:8000/api/books/ \
  -H 'Content-Type: application/json' \
  -d '{"title":"Python em prática","author":"Ana Silva","publication_date":"2024-01-15","summary":"Introdução prática à linguagem."}'

# consultar por título e autor (filtros combinados por AND)
curl 'http://127.0.0.1:8000/api/books/?title=python&author=ana&page=1&page_size=20'
```

## Verificação

```bash
pytest
ruff check config apps tests/library tests/chat tests/search scripts manage.py
python manage.py makemigrations --check --dry-run
```

A suíte usa SQLite temporário, não acessa a rede e não baixa modelos.
