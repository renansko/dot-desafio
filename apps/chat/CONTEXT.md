# Chatbot — Q2

Estado: chat validado anteriormente com OpenAI real; camada de avaliação prévia
implementada com testes offline, ainda sem validação semântica real.

Há um relato de recusa indevida de pergunta sobre serializers do DRF, pendente de
diagnóstico, registrado em [dificuldades e limitações](../../docs/dificuldades.md).

## Responsabilidade e boundaries

Responder sobre programação Python, sem persistência, ferramentas executáveis, RAG ou autenticação.
`apps/chat/presentation` valida a estrutura HTTP; `apps/chat/application` contém mensagens, limites,
interface específica de provedor e caso de uso, sem Django/LangChain/FAISS.
`apps/chat/infrastructure` lê configuração e integra ChatOpenAI/ChatAnthropic via LangChain.
O histórico é explícito; cada chamada contém apenas as mensagens enviadas nessa requisição.
A instrução do sistema é criada pelo servidor e enviada separadamente. Histórico admite somente
`user`/`assistant`; instruções em texto continuam sendo conteúdo não confiável. O escopo Python
é avaliado antes da geração, junto com risco de prompt injection. A avaliação reduz o risco,
mas não garante segurança. Contrato e política em
[ChatTrustLayer](../../docs/brain/conventions/ChatTrustLayer.md).

## Contrato HTTP

`POST /api/chat/`, Content-Type `application/json`:

```json
{"question":"Como criar uma lista em Python?","history":[]}
```

Resposta 200 (ilustrativa; texto varia com o modelo):

```json
{"answer":"Use colchetes: numeros = [1, 2, 3]."}
```

Para escopo Python abaixo de 0,85 ou risco de injeção a partir de 0,15, retorna 200 com
`{"answer":"Posso ajudar com programação Python. Reformule sua pergunta nesse contexto."}`,
sem geração. A avaliação considera todo o histórico; os scores ficam internos à aplicação.

Continuação:

```json
{"question":"Como adicionar um item nessa lista?","history":[{"role":"user","content":"Como criar uma lista em Python?"},{"role":"assistant","content":"Use colchetes: numeros = [1, 2, 3]."}]}
```

`history` é opcional e assume `[]`. Nenhuma ordem/alternância é exigida; mensagens são
preservadas na ordem enviada. `question` e `content` exigem strings não vazias após considerar
espaços; o texto original é preservado. Campos desconhecidos não são usados como instruções.
Schema OpenAPI: `/api/schema/`; interface: `/api/docs/`.

| Status | Condição | Exemplo de corpo |
| --- | --- | --- |
| 400 | Estrutura inválida, papel proibido, texto vazio ou limite excedido | `{"detail":"Pergunta ou histórico inválido."}` |
| 503 | Configuração inválida/ausente, autenticação, rate limit, avaliação inválida/indisponível ou resposta sem texto | `{"detail":"Dependência indisponível."}` |
| 504 | Timeout do SDK | `{"detail":"Tempo limite da dependência excedido."}` |
| 500 | Falha inesperada | `{"detail":"Erro interno do servidor."}` |

Mensagens 400 de limites identificam o limite. Nunca são devolvidos erros internos do SDK.

## Configuração e limites

Variáveis lidas ao utilizar chat; biblioteca não exige credenciais de IA. `.env` não é
carregado automaticamente: exporte as variáveis antes de iniciar o servidor.

| Variável | Padrão | Regra |
| --- | --- | --- |
| CHAT_PROVIDER | openai | openai ou anthropic; sem fallback |
| CHAT_MODEL | obrigatório | Modelo disponível na conta do provedor selecionado |
| OPENAI_API_KEY / ANTHROPIC_API_KEY | obrigatório | Somente chave do provedor selecionado |
| TYPESAFE_API_KEY | vazia | Presente: avaliação via Jev; ausente: saída estruturada do provedor do chat |
| TYPESAFE_MODEL | jev-latest | Modelo Jev; usado somente com chave TypeSafe |
| CHAT_DECISION_LOG_PATH | var/log/chat-decisions.log | Auditoria JSONL; 5 MB por arquivo e três backups |
| CHAT_TIMEOUT_SECONDS | 30 | Inteiro positivo; timeout de rede do SDK, sem retries |
| CHAT_MAX_OUTPUT_TOKENS | 1024 | Inteiro positivo, teto enviado ao modelo |
| CHAT_MAX_QUESTION_CHARS | 4000 | Inteiro positivo |
| CHAT_MAX_MESSAGE_CHARS | 4000 | Inteiro positivo por mensagem anterior |
| CHAT_MAX_HISTORY_MESSAGES | 20 | Inteiro positivo |
| CHAT_MAX_TOTAL_CHARS | 16000 | Inteiro positivo, pergunta + conteúdo do histórico |
| LANGSMITH_TRACING | false | true/false; true exige LANGSMITH_API_KEY |

Caracteres são pontos de código Python (`len`), incluindo espaços; limites são inclusivos.
O total exclui papéis e instrução de sistema. Esses limites reduzem tamanho/custo, mas não
substituem a janela de tokens específica de cada modelo. Timeout não é um prazo global HTTP:
avaliação e geração são sequenciais, cada uma com seu timeout. Falhas da avaliação nunca
liberam geração nem causam troca de avaliador. OpenAI exige modelo com JSON Schema;
Anthropic usa saída estruturada por tool calling, sem ferramentas executáveis.
Jev é integrado via HTTP com duas perguntas Noul por requisição, sem atualizar LangChain.
Com TypeSafe, pergunta e histórico também são enviados a esse provedor.
LangSmith fica explicitamente desativado por padrão, inclusive se houver configuração legada
`LANGCHAIN_TRACING_V2`; quando ativado, usa também `LANGSMITH_PROJECT` opcional.

Cada avaliação concluída gera um evento `chat_assessment` no stdout do servidor e no arquivo
definido por `CHAT_DECISION_LOG_PATH`. O evento registra avaliador (`typesafe`, `openai` ou
`anthropic`), modelo, request ID quando fornecido, scores, limites, decisão e duração. Não
registra pergunta, histórico ou credenciais. `decision=reject_scope` indica escopo abaixo do
limite; `reject_injection`, risco no limite ou acima; `generate`, chamada geradora autorizada.
Assim, `evaluator=typesafe` é a evidência de que aquela requisição usou Jev. A chamada HTTP
direta ao Jev não aparece no LangSmith.

```bash
tail -f var/log/chat-decisions.log
```

## Testes e demonstração real

```bash
.venv/bin/pytest tests/chat
.venv/bin/ruff check config apps tests/library tests/chat scripts manage.py
```

Testes bloqueiam conexões de rede no módulo, usam doubles para ambos os provedores e
exercitam os construtores LangChain sem invocar modelos. Cobrem sucesso, continuação,
configuração, falhas externas, seleção de Jev, saída estruturada, bloqueio da geração e
entradas imediatamente abaixo/no/acima de cada limite. Não medem precisão semântica real.

Uma avaliação real opcional usa os 100 casos rotulados em `evaluation/chat.json`:

```bash
python manage.py eval_chat
```

O comando faz uma chamada ao avaliador por caso e grava métricas e casos incorretos
em `var/evaluation/chat.json`. Os limites padrão são 95% de acurácia, até 5% de
bloqueios indevidos e zero ataques aceitos; as flags `--min-accuracy`,
`--max-legitimate-block-rate` e `--max-attack-acceptance-rate` permitem ajustá-los.
Falhas externas reprovam a execução sem gravar detalhes. O conjunto e as metas são
testes exploratórios do projeto, não requisitos do PDF nem evidência de qualidade
até serem executados com uma integração real.

Demonstração real **separada da suíte**, com duas requisições HTTP. Quando aceitas,
custam quatro chamadas externas: duas avaliações e duas gerações:

```bash
source .venv/bin/activate
# Configure OPENAI_API_KEY no ambiente local, sem versionar ou compartilhar a chave.
export CHAT_PROVIDER=openai
export CHAT_MODEL=gpt-4o-mini  # ou um modelo compatível disponível na conta
export LANGSMITH_TRACING=false
python manage.py runserver
# Em outro terminal, na raiz:
.venv/bin/python -m scripts.demo_chat
```

O script faz duas requisições HTTP ao servidor local: a pergunta exigida e uma continuação
com a resposta real anterior no histórico. Verifique se a primeira explica criação de listas
e a segunda explica adição de itens. Não registrar credenciais na evidência.
A demonstração real foi executada com OpenAI pelo responsável pelo projeto. Não registrar
credenciais nem respostas que possam conter dados sensíveis na evidência.

Referências dos adaptadores: [ChatOpenAI](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI)
e [ChatAnthropic](https://reference.langchain.com/python/langchain-anthropic/chat_models/ChatAnthropic).
