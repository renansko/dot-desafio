# Busca Semântica

O contexto indexa documentos locais em trechos, gera embeddings e consulta documentos únicos por
similaridade. Ele é independente da Biblioteca e do Chatbot.

O comando `index_documents` lê o corpus JSON, preserva origem e identificador, e publica um
artefato FAISS com metadados. Vetores normalizados usam produto interno como similaridade cosseno.
Em uma consulta, todos os trechos são ordenados antes de deduplicar documentos.

O índice só abre quando provedor, modelo e configuração de trechos coincidem com seus metadados.
Uma reconstrução é publicada atomicamente, preservando o índice anterior em caso de falha.

O corpus, a preparação de embeddings, os limites e o contrato HTTP estão em
[CONTEXT.md](../../apps/search/CONTEXT.md).
O contrato OpenAPI de `/api/search/` distingue os status 200, 400, 503, 504 e 500 por
descrição e exemplo; todos os erros mantêm o campo `detail` com mensagem pública segura.
