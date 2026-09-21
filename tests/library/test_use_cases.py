from datetime import date

import pytest

from apps.library.application.errors import InvalidBook
from apps.library.application.ports import BookPage
from apps.library.application.use_cases import CreateBook, ListBooks


class FakeBookRepository:
    def __init__(self):
        self.added = None
        self.list_arguments = None

    def add(self, book):
        self.added = book
        return book

    def list(self, **kwargs):
        self.list_arguments = kwargs
        return BookPage(items=[], total=0)


def test_create_book_trims_and_sends_entity_to_port():
    repository = FakeBookRepository()

    book = CreateBook(repository).execute(
        title="  Python  ",
        author="  Ana  ",
        publication_date=date(2024, 1, 15),
        summary="  Guia  ",
    )

    assert book.title == "Python"
    assert repository.added == book


@pytest.mark.parametrize(
    ("field", "valid_length", "invalid_length"),
    [("title", 200, 201), ("author", 200, 201), ("summary", 5_000, 5_001)],
)
def test_create_book_accepts_limit_and_rejects_above_it(field, valid_length, invalid_length):
    repository = FakeBookRepository()
    values = {
        "title": "t",
        "author": "a",
        "publication_date": date(2024, 1, 15),
        "summary": "s",
    }
    values[field] = "x" * valid_length
    CreateBook(repository).execute(**values)
    values[field] = "x" * invalid_length

    with pytest.raises(InvalidBook) as error:
        CreateBook(repository).execute(**values)

    assert field in error.value.errors


@pytest.mark.parametrize("field", ["title", "author", "summary"])
def test_create_book_rejects_blank_text(field):
    values = {
        "title": "t",
        "author": "a",
        "publication_date": date(2024, 1, 15),
        "summary": "s",
    }
    values[field] = "   "

    with pytest.raises(InvalidBook) as error:
        CreateBook(FakeBookRepository()).execute(**values)

    assert field in error.value.errors


def test_list_books_passes_combined_filters_and_window_to_port():
    repository = FakeBookRepository()

    result = ListBooks(repository).execute(title="python", author="ana", offset=20, limit=20)

    assert result.total == 0
    assert repository.list_arguments == {
        "title": "python",
        "author": "ana",
        "offset": 20,
        "limit": 20,
    }


@pytest.mark.parametrize("length", [199, 200])
def test_list_books_accepts_filter_at_and_below_limit(length):
    ListBooks(FakeBookRepository()).execute(title="x" * length, author=None, offset=0, limit=100)


def test_list_books_rejects_filter_above_limit():
    with pytest.raises(InvalidBook):
        ListBooks(FakeBookRepository()).execute(title="x" * 201, author=None, offset=0, limit=20)
