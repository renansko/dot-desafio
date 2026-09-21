from apps.search.application.contracts import Chunk, Embeddings, IndexSpec, SearchIndex
from apps.search.application.errors import InvalidCorpus, InvalidSearch

MAX_QUERY_CHARS = 2000
MAX_RESULTS = 20


def validate_query(query, k):
    if not isinstance(query, str) or not query.strip():
        raise InvalidSearch("Consulta obrigatória e não vazia.")
    if len(query) > MAX_QUERY_CHARS:
        raise InvalidSearch(f"Consulta excede {MAX_QUERY_CHARS} caracteres.")
    if type(k) is not int or not 1 <= k <= MAX_RESULTS:
        raise InvalidSearch(f"k deve ser um inteiro entre 1 e {MAX_RESULTS}.")


def split_document(document, spec):
    if not document.text.strip():
        raise InvalidCorpus(f"Documento vazio: {document.source}")
    chunks = []
    for offset in range(0, len(document.text), spec.chunk_size - spec.chunk_overlap):
        text = document.text[offset:offset + spec.chunk_size]
        if text.strip():
            chunks.append(
                Chunk(
                    document.id, document.source, text, offset,
                    document.title, document.url, document.metadata,
                )
            )
        if offset + spec.chunk_size >= len(document.text):
            break
    return chunks


def unique_matches(matches, k):
    # Rank every chunk before deduplication: top-k chunks may all belong to one document.
    documents = {}
    for match in matches:
        documents.setdefault(match.id, match)
    return list(documents.values())[:k]


class BuildIndex:
    def __init__(self, embeddings: Embeddings, index: SearchIndex, spec: IndexSpec):
        self.embeddings, self.index, self.spec = embeddings, index, spec

    def execute(self, documents):
        if not documents:
            raise InvalidCorpus("Corpus vazio: nenhum documento JSON encontrado.")
        chunks = [chunk for doc in documents for chunk in split_document(doc, self.spec)]
        vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
        self.index.replace(chunks, vectors, self.spec)
        return len(chunks)


class Search:
    def __init__(self, embeddings: Embeddings, index: SearchIndex, spec: IndexSpec):
        self.embeddings, self.index, self.spec = embeddings, index, spec

    def execute(self, query, k=5):
        validate_query(query, k)
        snapshot = self.index.open(self.spec)
        vector = self.embeddings.embed_query(query)
        return unique_matches(snapshot.rank(vector), k)
