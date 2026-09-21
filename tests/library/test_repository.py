from datetime import date

import pytest

from apps.library.domain.entities import Book
from apps.library.infrastructure.repositories import DjangoBookRepository


@pytest.mark.django_db
def test_repository_persists_and_filters_case_insensitively_with_and():
    repository = DjangoBookRepository()
    first = repository.add(Book("Python Essencial", "Ana Silva", date(2024, 1, 1), "A"))
    repository.add(Book("Python Web", "Bruno Lima", date(2024, 2, 1), "B"))

    page = repository.list(title="PYTHON", author="ana", offset=0, limit=20)

    assert first.id is not None
    assert page.total == 1
    assert page.items == [first]


@pytest.mark.django_db
def test_repository_returns_requested_slice_and_total():
    repository = DjangoBookRepository()
    for index in range(3):
        repository.add(Book(f"Livro {index}", "Autor", date(2024, 1, 1), "Resumo"))

    page = repository.list(title=None, author=None, offset=1, limit=1)

    assert page.total == 3
    assert [book.title for book in page.items] == ["Livro 1"]
