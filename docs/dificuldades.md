# Dificuldades e limitações observadas

## Q2 — Recusa indevida de pergunta sobre Django REST Framework

Registro: 2026-09-22. Status: relatado pelo responsável pelo projeto; pendente
de reprodução controlada e diagnóstico.

Em uma utilização com OpenAI, foi enviada a pergunta:

```json
{"question":"Como usar serializers do DRF"}
```

Resposta observada, conforme relato:

```json
{"answer":"Posso ajudar com programação Python. Reformule sua pergunta nesse contexto."}
```

O comportamento esperado é aceitar a pergunta e explicar serializers do Django
REST Framework, que pertence ao ecossistema Python. A recusa impede uma pergunta
legítima mesmo sem a palavra “Python” na entrada.

### Evidência e limites do diagnóstico

O prompt de classificação inclui bibliotecas e frameworks Python. O caso de uso
retorna a mensagem acima quando a avaliação reprova escopo ou risco de injeção.
A resposta isolada não distingue esses motivos nem comprova qual avaliador foi
utilizado: a configuração permite Jev mesmo quando a geração usa OpenAI.
Modelo, scores, decisão registrada e configuração da execução não foram fornecidos.
Não há causa confirmada nem correção validada para este relato.

Os testes offline verificam contratos e decisões com doubles; não demonstram a
qualidade semântica do classificador real. `evaluation/chat.json` reúne 100 casos
rotulados, incluindo perguntas sobre serializers e Django REST Framework, mas
ainda não foi executado contra o avaliador real. Este caso mostra a necessidade de
medir recusas indevidas em perguntas legítimas sobre bibliotecas e frameworks.

### Próximos passos propostos

- Reproduzir a pergunta e correlacionar o evento `chat_assessment`, registrando
  avaliador, modelo, scores e motivo da decisão, sem credenciais.
- Executar a suíte rotulada com `python manage.py eval_chat` e revisar falsos
  bloqueios de perguntas sobre DRF, Django e outros frameworks Python.
- Medir recusas indevidas separadamente de ataques aceitos antes de alterar
  prompts ou limiares. Uma ocorrência não permite estimar a acurácia geral.

Esses passos são propostas; uma suíte rotulada existe, mas seus resultados reais ainda não foram medidos nem validados.

### Relação com o desafio

A [especificação](../Prova%20-%20Backend%20IA.pdf), página 1, Questão 2, pede
exemplos de perguntas e respostas para demonstrar o funcionamento do chatbot.
Este registro documenta uma limitação encontrada nessa demonstração. O PDF não
estabelece pontuação específica para dificuldades, evals ou uma meta de 95%.

Referências: [contexto do chatbot](../apps/chat/CONTEXT.md) e
[política de avaliação](brain/conventions/ChatTrustLayer.md).
