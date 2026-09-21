# Busca semântica — Q3

Estado: implementada. Comando `index_documents`, API `/api/search/`, corpus em `apps/brain`,
embeddings LangChain e persistência FAISS disponíveis. Independente do chatbot e da biblioteca.

## Responsabilidades e boundaries

`application/contracts.py` define documentos, trechos, resultados e interfaces específicas de
embeddings/índice. `application/use_cases.py` divide documentos, indexa e busca documentos únicos;
essa camada não importa Django, LangChain, NumPy ou FAISS.

`infrastructure/` adapta arquivos UTF-8, configuração, LangChain e FAISS. `presentation/`
valida JSON e documenta OpenAPI. `management/commands/` traduz falhas em diagnósticos CLI.
O coletor `apps/brain/collect_corpus.py` produz a entrada oficial do indexador: um JSON por
documento em `apps/brain/documents/`, preservando identificador, título, texto, URL, origem e
metadados de citação.

## Corpus e indexação

`apps/brain/documents/*.json` contém documentos da Wikipedia e abstracts do arXiv; `expected.json`
associa consultas semânticas a documentos esperados. O comando lê recursivamente JSON UTF-8,
ordenados pelo caminho. Cada documento exige `identifier`, `source` e `text` não vazios; `title`,
`url` e `metadata` são preservados até a resposta HTTP. JSON inválido, documentos vazios ou
diretório sem documentos abortam toda a reconstrução com diagnóstico explícito.

O splitter usa janelas de caracteres com sobreposição, preservando texto original e offset.
FAISS `IndexFlatIP` recebe vetores normalizados: produto interno equivale a similaridade cosseno.
Cada documento recebe o score do seu melhor trecho. Todos os trechos são classificados antes da
deduplicação, evitando perder documentos quando os primeiros trechos pertencem ao mesmo arquivo.
Empates usam a ordem do corpus/offset. Não há limiar mínimo de relevância.

O arquivo ZIP contém `vectors.faiss` e `metadata.json`, sem pickle. Os metadados registram
provedor, modelo, revisão, versão do formato, splitter, tamanho/sobreposição, métrica, dimensão,
checksum do FAISS e todos os trechos/origens. A consulta exige correspondência exata da
configuração, mesmo se a dimensão coincidir. O checksum detecta corrupção acidental; índices
são artefatos locais confiáveis, não um formato de upload externo.

O novo arquivo é construído em temporário no mesmo diretório e publicado com `os.replace`
após flush/fsync. Falhas de embeddings, serialização ou publicação preservam o anterior.
Consultas já iniciadas mantêm o snapshot lido; a próxima abre a versão publicada. Reconstruções
concorrentes publicam versões completas; a última publicação vence. Não há atualização incremental.
Veja [ADR da persistência](adr/0001-persistencia-atomica.md).

## Configuração e limites

Django não lê `.env` automaticamente: exporte as variáveis indicadas em `.env.example`.

| Variável | Padrão | Limites/contrato |
| --- | --- | --- |
| `EMBEDDING_PROVIDER` | `local` | `local` ou `openai`, sem fallback |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` local; `text-embedding-3-small` OpenAI | Não vazio |
| `EMBEDDING_REVISION` | vazio | Revisão opcional do modelo local; faz parte da compatibilidade |
| `EMBEDDING_TIMEOUT_SECONDS` | 30 | 1–300 segundos; timeout do cliente OpenAI, sem retries |
| `SEARCH_INDEX_PATH` | `var/search/index.zip` | Caminho do artefato local |
| `SEARCH_CHUNK_SIZE` | 400 | 1–2000 caracteres |
| `SEARCH_CHUNK_OVERLAP` | 60 | 0 até tamanho do trecho menos 1 |

Credencial OpenAI só é exigida ao gerar embeddings OpenAI. `CHAT_*` não influencia a busca.
Tracing é desativado para embeddings. O modelo local usa CPU e somente arquivos já preparados
no cache; a API e a indexação não baixam modelos implicitamente. Instalação/modelo ausente gera
503 na busca. O extra `local-embeddings` instala LangChain Hugging Face e Sentence Transformers;
não é necessário para executar os testes determinísticos ou o provedor OpenAI.

O modelo local padrão é multilíngue (50+ idiomas), produz 384 dimensões e limita a entrada a 128 tokens
([model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)).
A escolha por um modelo multilíngue viabiliza busca semântica cross-lingual (por exemplo, consultas
em português recuperando documentos em inglês do corpus ou vice-versa, sem tradução prévia).
As janelas são em caracteres, não tokens: entradas longas podem ser truncadas pelo modelo.
O padrão de 400 caracteres favorece textos curtos; ajuste ao corpus/modelo e reconstrua.
O limite de consulta é 2000 caracteres, contado antes de remover espaços (o texto é preservado).
`k` deve ser inteiro JSON entre 1 e 20, padrão 5; strings, floats e booleanos são rejeitados.

Este índice exato carrega todo o corpus em memória, gera embeddings para todos os trechos e
ordena todos os candidatos. É destinado a corpus pequeno; não há paginação, filtro de acesso
ou garantia de latência para grandes coleções. O timeout é de transporte remoto, não um prazo
para execução local ou para todo o comando de indexação.

## Preparação e demonstração real (fora da suíte padrão)

Na raiz do projeto, com `.venv` ativado:

```bash
# CPU: instalar primeiro o Torch evita baixar bibliotecas CUDA desnecessárias.
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev,local-embeddings]'
export EMBEDDING_PROVIDER=local
export EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# Opcional: export EMBEDDING_REVISION=<commit-do-modelo>
python -m scripts.prepare_embeddings  # download explícito, requer rede e espaço em disco
python manage.py index_documents
python -m scripts.demo_search
```

A demonstração reconstrói o índice configurado, usa o comando e a API DRF no mesmo processo,
imprime scores e falha se o primeiro resultado divergir de `expected.json`. As consultas
avaliam associação semântica, não apenas coincidência literal:

| Consulta | Primeiro documento esperado |
| --- | --- |
| How can I select informative data points from a data stream? | `arxiv:2302.08893v4` |
| How do learning curves help choose a machine learning model? | `arxiv:2201.12150v2` |
| How can decisions made by machine learning models be explained? | `arxiv:2304.02381v2` |

Alternativa OpenAI, com `OPENAI_API_KEY` exportada no shell:

```bash
export EMBEDDING_PROVIDER=openai
export EMBEDDING_MODEL=text-embedding-3-small
python manage.py index_documents
python -m scripts.demo_search
```

Trocar provedor, modelo, revisão ou configuração de trechos exige reconstrução pelo mesmo
comando. Até reconstruir com sucesso, consultas na nova configuração recebem 503; o artefato
anterior continua utilizável com a configuração anterior. Editar o corpus também exige
reindexar; não há monitoramento automático. Para preservar a demonstração, use outro
`SEARCH_INDEX_PATH` ao indexar um corpus alternativo.

## HTTP e OpenAPI

```bash
python manage.py runserver
curl -X POST http://127.0.0.1:8000/api/search/ \
  -H 'Content-Type: application/json' \
  -d '{"query":"Como guardar dinheiro para imprevistos?","k":1}'
```

Exemplo de formato de resposta (score ilustrativo; depende do modelo):

```json
{"results":[{"id":"arxiv:2302.08893v4","source":"arxiv","title":"Active learning for data streams: a survey","url":"http://arxiv.org/abs/2302.08893v4","snippet":"...","score":0.72,"metadata":{"categories":["stat.ML"]}}]}
```

Resultados únicos em relevância decrescente. Se `k` superar o número de documentos, retorna
somente os disponíveis com 200. Corpus vazio nunca publica um índice. Erros usam `{"detail":"..."}`:
400 para consulta/quantidade inválida; 503 para configuração, índice ausente/incompatível/corrompido
ou embeddings indisponíveis; 504 para timeout remoto; 500 para falha inesperada sem detalhes internos.
A validação de entrada acontece antes de carregar índice/modelo. Contratos, limites e respostas
estão em `/api/schema/` e `/api/docs/`.

## Verificação

```bash
pytest tests/search
pytest
ruff check config apps tests/library tests/chat tests/search scripts manage.py
python manage.py spectacular --validate --file /tmp/dot-openapi.yaml
python manage.py makemigrations --check --dry-run
```

A suíte usa FAISS real, vetores determinísticos, diretórios temporários e rede bloqueada nos
testes de busca. Não instala nem carrega modelos, não baixa tokens e não exige credenciais.
Cobre persistência/reabertura, ordenação, deduplicação, empates, snapshots, falhas de reconstrução,
metadados incompatíveis/corrompidos, corpus vazio, erros HTTP e limites abaixo/no/acima.
