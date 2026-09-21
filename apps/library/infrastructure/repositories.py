from django.db import OperationalError

from apps.library.application.errors import DependencyUnavailable
from apps.library.application.ports import BookPage
from apps.library.domain.entities import Book
from apps.library.models import BookRecord


class DjangoBookRepository:
    def add(self, book: Book) -> Book:
        try:
            record = BookRecord.objects.create(
                title=book.title,
                author=book.author,
                publication_date=book.publication_date,
                summary=book.summary,
            )
        except OperationalError as exc:
            raise DependencyUnavailable from exc
        return _to_entity(record)

    def list(self, *, title: str | None, author: str | None, offset: int, limit: int) -> BookPage:
        try:
            records = BookRecord.objects.all()
            if title:
                records = records.filter(title__icontains=title)
            if author:
                records = records.filter(author__icontains=author)
            total = records.count()
            items = [_to_entity(record) for record in records[offset : offset + limit]]
        except OperationalError as exc:
            raise DependencyUnavailable from exc
        return BookPage(items=items, total=total)


def _to_entity(record: BookRecord) -> Book:
    return Book(
        id=record.id,
        title=record.title,
        author=record.author,
        publication_date=record.publication_date,
        summary=record.summary,
    )
