# ADR 0001 — Aplicação Python modular com Clean Architecture enxuta

Status: aceito para implementação.

## Contexto

O PDF exige Python e, na Q1, Django/Flask/FastAPI com SQLite. O projeto prioriza convenções integradas próximas da experiência com Laravel, baixo esforço de configuração e uma issue por questão.

## Decisão

Usar uma aplicação Django + DRF com três módulos. SQLite persiste livros; FAISS mantém o índice vetorial separado. Não adicionar Laravel, frontend, autenticação, deploy ou RAG neste escopo local.

Domínio e casos de uso não importam frameworks. Interfaces delimitam persistência, chat, embeddings e índice vetorial; infraestrutura implementa adaptadores. Views e serializers traduzem HTTP para casos de uso. Evitar repositórios genéricos e duplicação de validação sem necessidade.

LangChain integra chat e embeddings. Chat usa OpenAI por padrão, conforme Q2, com Anthropic/Claude alternativo. Embeddings usam modelo local multilíngue por padrão e OpenAI alternativo. Provedor/modelo de chat e de embeddings são configurações independentes. Não há fallback silencioso entre provedores.

Criar `.env.example` sem segredos durante Q1 e completá-lo nas demais questões. Ignorar `.env`, bancos e índices locais. Validar configuração apenas da capacidade/provedor utilizado: ausência de credenciais de IA não deve impedir usar a biblioteca. LangSmith é opcional e desativado por padrão.

Erros HTTP: entrada inválida 400, dependência/configuração indisponível 503, timeout externo 504, falha inesperada 500 sem detalhes internos. Testes usam adaptadores simulados e SQLite temporário, sem rede ou cobrança. Verificações reais são separadas. Ruff C901 limita a complexidade da aplicação a 5, excluindo migrations geradas.

## Consequências

Há uma base operacional única e três contextos documentados. Q2/Q3 aguardam a base de Q1, mas são independentes entre si. A separação exige pequenos adaptadores; não exige infraestrutura distribuída. Trocar embeddings exige reconstruir o índice, mesmo quando a dimensão do vetor não muda.

## Organização dos pacotes

Os módulos próprios ficam sob `apps/` (`apps.library`, `apps.chat`, `apps.search` e `apps.brain`).
`brain` continua sendo um utilitário de coleta, sem registro em `INSTALLED_APPS`.
Configuração Django e suporte permanecem em `config/`, `scripts/`, `docs/` e `tests/`.
O label Django da biblioteca continua `library`; mover o pacote não altera tabelas
nem o histórico de migrations.
