# Corpus de testes

Este diretório armazena o corpus local usado nos experimentos de busca semântica/RAG.

Comece com 100–1.000 documentos limpos, provenientes de Wikipedia e arXiv. Cada
documento deve preservar, quando disponível, título, texto, URL de origem e
metadados necessários para citar a fonte na resposta.

Não versione corpus grande ou artefatos gerados de índice/embeddings neste
repositório; use apenas amostras pequenas e apropriadas para testes.

## Coleta inicial

O script `collect_corpus.py` baixa artigos da Wikipedia e abstracts do arXiv,
normalizados como um JSON por documento em `apps/brain/documents/`. Ele preserva
identificador, título, texto, URL e metadados de citação.

```bash
python3 apps/brain/collect_corpus.py \
  --topic "machine learning" \
  --topic "natural language processing" \
  --wikipedia-limit 10 \
  --arxiv-limit 10
```

O padrão de 3 segundos entre temas limita a pressão sobre a API do arXiv. A
coleta é uma demonstração com rede; os testes usam respostas simuladas.

O indexador da Q3 lê esses JSONs diretamente; não é necessário convertê-los
para `.txt`. Os 23 documentos atuais são versionados. `expected.json` contém
consultas semânticas para a demonstração: `expected_id` é a expectativa com
OpenAI; `expected_id_local` substitui essa expectativa quando o modelo local
retorna outro documento.

Para completar um diretório até uma quantidade exata sem repetir URLs já
armazenadas, acrescente `--target-total`. Por exemplo, para chegar a 50:

```bash
python3 apps/brain/collect_corpus.py --topic "computer vision" --target-total 50
```
