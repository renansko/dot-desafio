# Biblioteca

O contexto Biblioteca administra somente o cadastro e a consulta de livros. Um livro tem título,
autor, data de publicação e resumo; não há empréstimos, autenticação, edição ou exclusão.

`POST /api/books/` cria um livro e `GET /api/books/` o consulta por trechos de título e autor,
sem diferenciar maiúsculas de minúsculas. Quando os dois filtros existem, a consulta usa AND.

O fluxo é HTTP/serializer, caso de uso, porta de repositório e adaptador Django ORM. Domínio e
casos de uso não dependem de Django. SQLite é o armazenamento da aplicação.

A listagem é paginada e devolve `count`, links `next` e `previous`, e `results`. Os detalhes de
campos, limites e erros estão em [CONTEXT.md](../../apps/library/CONTEXT.md).
