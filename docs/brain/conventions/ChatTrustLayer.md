# Camada de confiança do Chat

Estado: implementada na Q2; validada com doubles, sem avaliação semântica real nesta entrega.

## Intenção

Avaliar escopo Python e tentativa de manipular instruções antes da geração. O
caso de uso recebe dois scores separados: `python_probability` e
`injection_probability`. A avaliação inclui pergunta e histórico completo validado.

Fluxo:

`entrada validada -> classificador -> política da aplicação -> geração ou recusa`

## Seleção do avaliador

- `TYPESAFE_API_KEY` não vazia: Jev pela API HTTP TypeSafe, com duas perguntas `Noul`
  na mesma chamada. Modelo em `TYPESAFE_MODEL`, padrão `jev-latest`.
- Sem essa chave: o provedor de `CHAT_PROVIDER` classifica usando `CHAT_MODEL`.
  OpenAI usa JSON Schema estrito; Anthropic usa saída estruturada via tool calling,
  sem executar ferramentas. Ambos permanecem atrás dos adaptadores LangChain.
- Falha do avaliador selecionado não troca de provedor nem libera a geração.

Jev é o modelo da TypeSafe AI, não LangGraph. O adaptador HTTP evita atualizar a
família LangChain apenas para instalar a integração recente `langchain-typesafe`.

## Política e limites

- Geração exige `python_probability >= 0.85` e `injection_probability < 0.15`.
- Fora desses limites, retorna 200 com `answer` fixo pedindo reformulação sobre
  Python, sem chamar o gerador. Scores não são expostos no contrato HTTP.
- Scores ausentes, inválidos, não finitos ou fora de 0–1 são falhas da dependência.
- Falhas da avaliação retornam 503; timeout retorna 504. Nenhuma libera a geração.
- Uma pergunta aceita exige duas chamadas sequenciais; uma recusada exige uma.
  `CHAT_TIMEOUT_SECONDS` vale por chamada, não como prazo global da requisição.
- A chave TypeSafe implica enviar também pergunta e histórico a esse provedor.
  A integração HTTP TypeSafe não gera traces LangSmith. O fallback LangChain
  respeita o tracing opcional já existente.

## Auditoria da decisão

Cada avaliação concluída produz JSONL no stdout e em `CHAT_DECISION_LOG_PATH`
(padrão `var/log/chat-decisions.log`, rotação em 5 MB e três backups). O evento
contém avaliador, modelo, request ID quando disponível, scores, limites, decisão
e duração. Pergunta, histórico e credenciais são excluídos. `evaluator=typesafe`
confirma uso do Jev; `openai` ou `anthropic` identifica o fallback estruturado.

Os valores de `decision` são `reject_scope`, `reject_injection` e `generate`.
Quando as duas recusas se aplicam, injeção prevalece como motivo registrado. O
log é diagnóstico operacional local e não substitui uma trilha de auditoria com
retenção, controle de acesso e correlação HTTP em produção.

Classificar escopo não detecta toda injeção. Por isso há uma avaliação de risco
separada e instruções de sistema preservadas na geração. Conteúdo do cliente,
inclusive mensagens com papel `assistant`, nunca é confiável. A camada reduz o
risco, mas não é uma garantia de segurança nem valida a resposta gerada.

Os limites são iniciais. Scores declarados pelo LLM não são probabilidades
calibradas; os de Jev também precisam ser avaliados neste domínio. Validar com
perguntas Python, continuações, ambiguidades, fora do escopo e ataques no histórico;
medir falsos aceites, falsas recusas, calibração, custo e latência por provedor.

## Relação com o código

Contrato e política: `apps/chat/application/use_cases.py`. Adaptadores e validação
externa: `apps/chat/infrastructure/classification.py`. O domínio não importa
SDKs, Django ou LangChain. Testes offline verificam roteamento e contratos, não
comprovam a capacidade semântica dos modelos de reconhecer ataques reais.

Referências externas: [API TypeSafe](https://docs.typesafe.ai/introduction/quickstart)
e [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Referências: [Chatbot](../Chatbot.md) e
[contexto do módulo](../../../apps/chat/CONTEXT.md).
