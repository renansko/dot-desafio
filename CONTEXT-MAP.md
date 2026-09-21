# Mapa de contextos

Estado: Q1, Q2 e Q3 implementadas; demonstração real da Q2 pendente de credencial.

| Questão | Contexto | Responsabilidade |
| --- | --- | --- |
| Q1 | [Biblioteca](apps/library/CONTEXT.md) | Cadastrar e consultar livros |
| Q2 | [Chatbot](apps/chat/CONTEXT.md) | Responder perguntas sobre programação Python |
| Q3 | [Busca semântica](apps/search/CONTEXT.md) | Indexar textos e recuperar documentos por similaridade |

Decisões compartilhadas: [ADRs gerais](docs/adr/0001-arquitetura-do-desafio.md). Decisões específicas ficam no diretório `adr/` de cada contexto quando necessárias.

Q1 fornece a base da aplicação. Q2 e Q3 dependem dessa base, mas não dependem entre si. Não há RAG conectando chatbot e busca nesta entrega.
