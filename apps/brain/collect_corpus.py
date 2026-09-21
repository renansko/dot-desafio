"""Coleta um pequeno corpus citável da Wikipedia e do arXiv.

Uso de exemplo (requer rede):
    python apps/brain/collect_corpus.py --topic "machine learning" --topic "Python programming"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import xml.etree.ElementTree as element_tree
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_REST_API = "https://en.wikipedia.org/w/rest.php/v1"
ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "dot-desafio-corpus-collector/0.1 (local RAG experiment)"
ATOM = "{http://www.w3.org/2005/Atom}"


class CollectionError(Exception):
    """A fonte externa não respondeu com um documento utilizável."""


class TextExtractor(HTMLParser):
    """Converte HTML em texto sem introduzir uma dependência no experimento."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass(frozen=True)
class CorpusDocument:
    identifier: str
    source: str
    title: str
    text: str
    url: str
    metadata: dict[str, Any]


Opener = Callable[..., Any]


def request_text(url: str, opener: Opener = urlopen) -> str:
    request = Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with opener(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except OSError as error:
        raise CollectionError(f"Não foi possível coletar {url}: {error}") from error


def request_json(url: str, opener: Opener = urlopen) -> dict[str, Any]:
    try:
        return json.loads(request_text(url, opener))
    except json.JSONDecodeError as error:
        raise CollectionError(f"Resposta JSON inválida de {url}") from error


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def wikipedia_documents(
    topic: str, limit: int, sleep_seconds: float = 1.1, opener: Opener = urlopen
) -> list[CorpusDocument]:
    query = urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "srnamespace": 0,
            "srlimit": limit,
            "format": "json",
        }
    )
    pages = request_json(f"{WIKIPEDIA_API}?{query}", opener).get("query", {}).get("search", [])
    documents = []
    for page in pages:
        title = page["title"]
        key = quote(title.replace(" ", "_"), safe="")
        text = html_to_text(request_text(f"{WIKIPEDIA_REST_API}/page/{key}/html", opener))
        if text:
            documents.append(
                CorpusDocument(
                    identifier=f"wikipedia:{page['pageid']}",
                    source="wikipedia",
                    title=title,
                    text=text,
                    url=f"https://en.wikipedia.org/wiki/{key}",
                    metadata={
                        "topic": topic,
                        "license": "CC BY-SA 4.0",
                        "language": "en",
                        "page_id": page["pageid"],
                    },
                )
            )
        time.sleep(sleep_seconds)
    return documents


def entry_text(entry: element_tree.Element, field: str) -> str:
    return (entry.findtext(f"{ATOM}{field}") or "").strip()


def arxiv_documents(topic: str, limit: int, opener: Opener = urlopen) -> list[CorpusDocument]:
    query = urlencode(
        {"search_query": f"all:{topic}", "start": 0, "max_results": limit, "sortBy": "relevance"}
    )
    try:
        root = element_tree.fromstring(request_text(f"{ARXIV_API}?{query}", opener))
    except element_tree.ParseError as error:
        raise CollectionError("Resposta Atom inválida do arXiv") from error
    documents = []
    for entry in root.findall(f"{ATOM}entry"):
        url = entry_text(entry, "id")
        identifier = url.rsplit("/", maxsplit=1)[-1]
        text = entry_text(entry, "summary")
        if text:
            documents.append(
                CorpusDocument(
                    identifier=f"arxiv:{identifier}",
                    source="arxiv",
                    title=entry_text(entry, "title"),
                    text=text,
                    url=url,
                    metadata={
                        "topic": topic,
                        "authors": [author.findtext(f"{ATOM}name") for author in entry.findall(f"{ATOM}author")],
                        "categories": [category.attrib["term"] for category in entry.findall(f"{ATOM}category")],
                        "published": entry_text(entry, "published"),
                        "updated": entry_text(entry, "updated"),
                    },
                )
            )
    return documents


def document_path(output_dir: Path, document: CorpusDocument) -> Path:
    digest = hashlib.sha256(document.url.encode()).hexdigest()[:12]
    return output_dir / f"{document.source}-{digest}.json"


def existing_urls(output_dir: Path) -> set[str]:
    if not output_dir.exists():
        return set()
    return {json.loads(path.read_text(encoding="utf-8"))["url"] for path in output_dir.glob("*.json")}


def new_documents(documents: list[CorpusDocument], known_urls: set[str]) -> list[CorpusDocument]:
    unique = []
    for document in documents:
        if document.url not in known_urls:
            unique.append(document)
            known_urls.add(document.url)
    return unique


def save_documents(documents: list[CorpusDocument], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for document in documents:
        path = document_path(output_dir, document)
        path.write_text(json.dumps(asdict(document), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coleta textos para o corpus RAG local.")
    parser.add_argument("--topic", action="append", required=True, help="Tema a pesquisar; repita para mais temas.")
    parser.add_argument("--wikipedia-limit", type=int, default=10, help="Máximo por tema (padrão: 10).")
    parser.add_argument("--arxiv-limit", type=int, default=10, help="Máximo por tema (padrão: 10).")
    parser.add_argument("--output", type=Path, default=Path("apps/brain/documents"))
    parser.add_argument(
        "--target-total", type=int, help="Total de documentos distintos desejado no diretório de saída."
    )
    parser.add_argument(
        "--wikipedia-sleep-seconds", type=float, default=1.1, help="Pausa entre artigos (padrão: 1.1)."
    )
    parser.add_argument("--sleep-seconds", type=float, default=3, help="Pausa entre consultas ao arXiv.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents: list[CorpusDocument] = []
    for topic in args.topic:
        if args.wikipedia_limit:
            documents.extend(wikipedia_documents(topic, args.wikipedia_limit, args.wikipedia_sleep_seconds))
        if args.arxiv_limit:
            documents.extend(arxiv_documents(topic, args.arxiv_limit))
            time.sleep(args.sleep_seconds)
    urls = existing_urls(args.output)
    current_total = len(urls)
    documents = new_documents(documents, urls)
    if args.target_total is not None:
        remaining = max(0, args.target_total - current_total)
        documents = documents[:remaining]
    paths = save_documents(documents, args.output)
    total = len(existing_urls(args.output))
    print(f"{len(paths)} novos documentos armazenados; total: {total} em {args.output}")


if __name__ == "__main__":
    main()
