# Convenções do projeto

Desafio descrito em `Prova - Backend IA.pdf`. Há uma issue por questão; não implementar funcionalidades fora da issue em trabalho. As docs descrevem contratos planejados, não funcionalidades já disponíveis.

## Arquitetura e qualidade

- Python com Django + Django REST Framework (DRF); SQLite para livros.
- Uma aplicação com módulos biblioteca, chatbot e busca semântica.
- Clean Architecture enxuta: domínio e casos de uso independentes de Django, LangChain e FAISS; adaptadores nos limites externos. Não criar bases genéricas sem necessidade.
- Cada entrega inclui testes de comportamento, erros, casos de borda e atualização do contexto do módulo.
- Complexidade ciclomática máxima de 5 por função da aplicação, verificada por Ruff C901 quando a base for implementada. Excluir migrations geradas.
- Testes padrão sem rede, modelos baixados ou credenciais. Integrações reais são verificações explícitas separadas.
- Comentar decisões e lógica não óbvias. Nunca versionar segredos.

## Agent skills

### Issue tracker

Issues no GitHub `renansko/dot-desafio`. Veja `docs/agents/issue-tracker.md`.

### Triage labels

Vocabulário padrão das skills; novas issues recebem `needs-triage`. Veja `docs/agents/triage-labels.md`.

### Domain docs

Contexto por módulo, mapeado em `CONTEXT-MAP.md`. Veja `docs/agents/domain.md`.

# Instruções para Agentes

## Desenvolvimento Orientado a Testes (TDD Obrigatório)

Sempre comece qualquer demanda, nova funcionalidade ou correção de bug utilizando o fluxo de **TDD (Red-Green-Refactor)**:

1. **Red**: Escreva primeiro um teste que falha (expressando o comportamento, entrada/saída e contratos esperados).
2. **Green**: Implemente o código mínimo necessário para fazer o teste passar.
3. **Refactor**: Melhore a qualidade, arquitetura e limpeza do código mantendo a suíte de testes verde.
4. **Regra de Ouro**: Nunca escreva código de produção sem um teste prévio que falhe. Em correções de bugs, sempre reproduza a falha com um teste antes da correção.
5. Referência: [/tdd (aihero.dev)](https://www.aihero.dev/skills-tdd).

## Brain de Contexto

Antes de alterar módulos já documentados, leia [docs/brain/index.md](docs/brain/index.md) e consulte as páginas relacionadas.

O Brain registra contratos, invariantes, decisões, relações entre módulos e regras que não são fáceis de inferir apenas do código. Ele não substitui testes, ADRs ou documentação de API.

Quando uma alteração modificar comportamento, contrato, efeito colateral, integração ou regra de produto, atualize o código e o Brain no mesmo trabalho.

### Regras de Manutenção do Brain:

- confirme contratos importantes no código e nos testes antes de editar a documentação;
- não duplique implementação nem crie páginas para código trivial;
- corrija documentação obsoleta junto com a mudança que a tornou obsoleta;
- mantenha cada página Markdown (`.md`) do Brain com menos de 100 linhas;
- use nomes estáveis em `PascalCase` para páginas conceituais;
- mantenha links relativos e âncoras válidos;
- atualize o índice (`docs/brain/index.md`) quando páginas forem criadas, removidas ou renomeadas;
- registre mudanças relevantes em `docs/brain/log.md` no formato: `data | issue/PR | escopo`;
- nunca inclua segredos, credenciais, tokens, payloads reais ou dados pessoais.

## Qualidade de Código e Complexidade Ciclomática
