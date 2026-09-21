from dataclasses import dataclass
from typing import Protocol

from apps.library.domain.entities import Book


@dataclass(frozen=True, slots=True)
class BookPage:
    items: list[Book]
    total: int


class BookRepository(Protocol):
    def add(self, book: Book) -> Book: ...

    def list(
        self, *, title: str | None, author: str | None, offset: int, limit: int
    ) -> BookPage: ...
