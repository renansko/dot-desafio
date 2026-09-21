# Biblioteca — Q1

Estado: Q1 implementada e verificável.

## Responsabilidade e vocabulário

Livro contém título, autor, data de publicação e resumo. Cadastro persiste um livro; consulta filtra os livros cadastrados. Não há edição, exclusão, empréstimos ou autenticação neste escopo.

## Fluxo e boundaries

HTTP/serializer → caso de uso → interface de persistência → adaptador Django ORM → SQLite. Domínio e casos de uso não importam Django. O adaptador traduz falhas de persistência para erros da aplicação.

## Contratos

- `POST /api/books/`: recebe `title`, `author`, `publication_date` (ISO `AAAA-MM-DD`) e
  `summary`; retorna 201 com os mesmos campos e `id`.
- `GET /api/books/`: aceita `title` e `author`, ambos parciais e sem distinção de caixa;
  quando combinados, aplica AND. `page` começa em 1 e `page_size` tem padrão 20 e máximo 100.
  Retorna `count`, links `next`/`previous` e `results`. Sem correspondência, retorna lista vazia
  com 200.
- `title` e `author` são obrigatórios, não vazios e têm até 200 caracteres; `summary` é
  obrigatório, não vazio e tem até 5.000 caracteres. Filtros têm até 200 caracteres.
- Entrada inválida: 400; indisponibilidade de persistência/configuração: 503; timeout de
  dependência externa: 504; erro inesperado: 500. Respostas 5xx não expõem detalhes internos.
- OpenAPI: `GET /api/schema/`; interface Swagger: `GET /api/docs/`.

## Verificação e exemplos

```http
POST /api/books/
Content-Type: application/json

{"title":"Python em prática","author":"Ana Silva","publication_date":"2024-01-15","summary":"Introdução prática à linguagem."}
```

```http
GET /api/books/?title=python&author=ana&page=1&page_size=20
```

Executar `pytest` para casos de uso com adaptador simulado, persistência e endpoints com SQLite
temporário. Executar `ruff check config apps tests/library manage.py` para lint e C901
(complexidade máxima 5) e
`python manage.py makemigrations --check --dry-run` para verificar migrations. Esses comandos
não usam rede, credenciais ou modelos externos.

Código em `apps/library/`, registrado como `apps.library.apps.LibraryConfig`.
O label Django `library` permanece estável para preservar migrations e tabelas existentes.
