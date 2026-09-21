from dataclasses import dataclass
from datetime import date

from apps.library.application.errors import InvalidBook
from apps.library.application.ports import BookPage, BookRepository
from apps.library.domain.entities import Book

TITLE_MAX_LENGTH = 200
AUTHOR_MAX_LENGTH = 200
SUMMARY_MAX_LENGTH = 5_000
FILTER_MAX_LENGTH = 200


@dataclass(frozen=True, slots=True)
class CreateBook:
    repository: BookRepository

    def execute(self, *, title: str, author: str, publication_date: date, summary: str) -> Book:
        errors = _book_errors(title, author, publication_date, summary)
        if errors:
            raise InvalidBook(errors)
        book = Book(
            title=title.strip(),
            author=author.strip(),
            publication_date=publication_date,
            summary=summary.strip(),
        )
        return self.repository.add(book)


@dataclass(frozen=True, slots=True)
class ListBooks:
    repository: BookRepository

    def execute(
        self, *, title: str | None, author: str | None, offset: int, limit: int
    ) -> BookPage:
        errors = _filter_errors(title, author, offset, limit)
        if errors:
            raise InvalidBook(errors)
        return self.repository.list(title=title, author=author, offset=offset, limit=limit)


def _book_errors(
    title: str, author: str, publication_date: date, summary: str
) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    _validate_text(errors, "title", title, TITLE_MAX_LENGTH)
    _validate_text(errors, "author", author, AUTHOR_MAX_LENGTH)
    _validate_text(errors, "summary", summary, SUMMARY_MAX_LENGTH)
    if not isinstance(publication_date, date):
        errors["publication_date"] = ["Informe uma data válida."]
    return errors


def _filter_errors(
    title: str | None, author: str | None, offset: int, limit: int
) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    if title is not None:
        _validate_text(errors, "title", title, FILTER_MAX_LENGTH)
    if author is not None:
        _validate_text(errors, "author", author, FILTER_MAX_LENGTH)
    if offset < 0:
        errors["offset"] = ["Deve ser maior ou igual a zero."]
    if not 1 <= limit <= 100:
        errors["limit"] = ["Deve estar entre 1 e 100."]
    return errors


def _validate_text(
    errors: dict[str, list[str]], field: str, value: object, max_length: int
) -> None:
    if not isinstance(value, str) or not value.strip():
        errors[field] = ["Este campo não pode ficar em branco."]
    elif len(value) > max_length:
        errors[field] = [f"Certifique-se de que tenha no máximo {max_length} caracteres."]
