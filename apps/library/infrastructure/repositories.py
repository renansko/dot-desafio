from django.db import OperationalError

from apps.library.application.errors import DependencyUnavailable
from apps.library.application.ports import BookPage
from apps.library.domain.entities import Book
from apps.library.models import BookRecord


class DjangoBookRepository:
    """Implementação do BookRepository utilizando o ORM do Django e SQLite."""

    def add(self, book: Book) -> Book:
        """Persiste uma nova entidade Book no banco e retorna a entidade com o ID gerado."""
        try:
            record = BookRecord.objects.create(
                title=book.title,
                author=book.author,
                publication_date=book.publication_date,
                summary=book.summary,
            )
        except OperationalError as exc:
            # Traduz falhas de persistência para erro da aplicação, isolando detalhes do banco
            raise DependencyUnavailable from exc
        return _to_entity(record)

    def list(self, *, title: str | None, author: str | None, offset: int, limit: int) -> BookPage:
        """Retorna uma página de livros aplicando filtros opcionais e paginação por fatia."""
        try:
            records = BookRecord.objects.all()
            # Filtros parciais case-insensitive exigidos pela especificação da Q1
            if title:
                records = records.filter(title__icontains=title)
            if author:
                records = records.filter(author__icontains=author)
            total = records.count()
            # Converte apenas os registros da fatia atual para entidades de domínio
            items = [_to_entity(record) for record in records[offset : offset + limit]]
        except OperationalError as exc:
            raise DependencyUnavailable from exc
        return BookPage(items=items, total=total)


def _to_entity(record: BookRecord) -> Book:
    """Mapeia o modelo ORM do Django (BookRecord) para a entidade pura de domínio (Book)."""
    return Book(
        id=record.id,
        title=record.title,
        author=record.author,
        publication_date=record.publication_date,
        summary=record.summary,
    )
