# Índice do Brain

O Brain reúne contexto arquitetural e de domínio que não deve ser inferido apenas
do código. Ele complementa os contratos detalhados nos `CONTEXT.md` dos módulos.

## Como utilizar

Comece por este índice. Antes de alterar um conceito documentado, consulte sua
entidade, serviço, funções, recursos e convenções relacionadas.

## Categorias

- `entities/`: entidades, relacionamentos, estados e invariantes.
- `services/`: responsabilidades, dependências e efeitos colaterais dos módulos.
- `functions/`: contratos de funções públicas relevantes.
- `resources/`: formatos de entrada e saída e suas validações.
- `conventions/`: decisões e padrões transversais.
- `product/`: vocabulário e regras de produto.

## Páginas

- [Biblioteca](Biblioteca.md): livros, consulta e persistência SQLite.
- [ChatEvaluation](ChatEvaluation.md): métricas e avaliação real do classificador.
- [Chatbot](Chatbot.md): conversa Python e fronteira com provedores LLM.
- [BuscaSemantica](BuscaSemantica.md): corpus, embeddings, índice FAISS e consulta.

## Convenções

- [Camada de confiança do Chat](conventions/ChatTrustLayer.md): avaliação de escopo e injeção com Jev ou provedor do chat antes da resposta.
