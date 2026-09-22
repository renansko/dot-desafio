## What to build

Implementar uma camada de observabilidade, logs estruturados e auditoria para o backend, com rastreabilidade via OpenTelemetry e visualização no Grafana, reutilizando os padrões arquiteturais do projeto [llm-brain-backend](https://github.com/renansko/llm-brain-backend).

A instrumentação deve cobrir os fluxos da aplicação (em especial o chatbot e a busca semântica), registrando metadados operacionais essenciais sem violar a privacidade do usuário nem gerar custos excessivos de armazenamento.

### Diretrizes principais
- **Logs estruturados (JSON)**: registrar início e término de requisições, `request_id`, endpoint, método, status HTTP, latência/duração, provedor e modelo de IA utilizados, timeouts e exceções.
- **Tabela de Auditoria de IA (OpenLog)**: persistir em banco de dados uma tabela dedicada de auditoria para chamadas de modelos, registrando métricas de consumo e custo:
  - `request_id` (chave de correlação com traces e logs);
  - Provedor (`provider`) e modelo (`model`);
  - Contagem de tokens: `input_tokens` (prompt), `output_tokens` (completion) e `total_tokens`;
  - Latência da inferência (`latency_ms`);
  - Status da chamada (sucesso, timeout, erro);
  - Timestamp de início e término.
- **Privacidade e conformidade**: prompts completos, mensagens de histórico e respostas geradas pela LLM **não** devem ser gravados nos logs ou spans de auditoria por padrão.
- **OpenTelemetry + Grafana**: instrumentar o Django/DRF para emissão de traces e métricas com exportação OTLP compatível com a stack Grafana (Grafana Tempo/Loki/Prometheus ou OpenTelemetry Collector).
- **Resiliência**: o tracing remoto deve ser opcional/configurável via variáveis de ambiente, sem degradar ou travar a aplicação caso o coletor esteja indisponível.

## Acceptance criteria

- [ ] Middleware para geração e propagação de identificador único de requisição (`request_id` / `trace_id`) nos headers e contexto de log.
- [ ] Modelo de dados e migration para tabela de auditoria (ex.: `LLMAuditLog` / `OpenLog`) contendo `request_id`, `provider`, `model`, `input_tokens`, `output_tokens`, `total_tokens`, `latency_ms`, `status` e `created_at`.
- [ ] Interceptador / callback para extrair métricas de consumo de tokens (token usage) retornadas pelos provedores de LLM e embeddings.
- [ ] Logs locais estruturados em formato JSON contendo metadados operacionais (`request_id`, `endpoint`, `status_code`, `duration_ms`, `provider`, `model`, erros e timeouts).
- [ ] Mecanismo de higienização de logs garantindo que prompts, histórico de chat e respostas não sejam expostos nos logs.
- [ ] Instrumentação com OpenTelemetry Python SDK (Django/DRF) configurada para exportação OTLP (métricas de tokens e latência disponíveis para o Grafana).
- [ ] Variáveis de ambiente para controle de tracing e endpoint do coletor (ex.: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_ENABLED=false` por padrão nos testes).
- [ ] Testes automatizados cobrindo o registro na tabela de auditoria, cálculo de tokens e injeção de `request_id` sem depender de serviços externos ou de rede.
- [ ] Documentação de configuração local e integração com o Grafana adicionada à documentação do projeto.

## Blocked by

- [x] Base da aplicação e contratos de API (Q1, Q2 e Q3 implementadas)
- [ ] Arquitetura de referência em [llm-brain-backend](https://github.com/renansko/llm-brain-backend)
