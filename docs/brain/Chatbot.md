# Chatbot

O Chatbot responde perguntas sobre programação Python. Cada requisição contém sua pergunta e o
histórico explícito; nenhuma conversa é persistida. A instrução de sistema é construída pelo
servidor e o histórico aceita apenas mensagens `user` e `assistant`.

O caso de uso não conhece Django ou LangChain. O adaptador de infraestrutura escolhe OpenAI ou
Anthropic pela configuração e usa LangChain para construir mensagens e invocar o modelo.

OpenAI é o padrão. A demonstração real com OpenAI foi validada pelo responsável pelo projeto,
com LangChain registrando a execução. Credenciais e conteúdo de conversas não entram no projeto.

Limites, variáveis de ambiente, contrato HTTP e mapeamento de falhas estão em
[CONTEXT.md](../../apps/chat/CONTEXT.md).
