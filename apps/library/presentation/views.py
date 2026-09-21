from django.urls import reverse
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.library.application.errors import InvalidBook
from apps.library.application.use_cases import CreateBook, ListBooks
from apps.library.infrastructure.repositories import DjangoBookRepository
from apps.library.presentation.serializers import (
    BookFilterSerializer,
    BookInputSerializer,
    BookOutputSerializer,
)


class BookListCreateView(APIView):
    repository_class = DjangoBookRepository

    @extend_schema(
        request=BookInputSerializer,
        responses={201: BookOutputSerializer},
        examples=[
            OpenApiExample(
                "Livro",
                value={
                    "title": "Python em prática",
                    "author": "Ana Silva",
                    "publication_date": "2024-01-15",
                    "summary": "Introdução prática à linguagem.",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = BookInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            book = CreateBook(self.repository_class()).execute(**serializer.validated_data)
        except InvalidBook as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookOutputSerializer(book).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter("title", str, description="Trecho do título (máximo 200 caracteres)."),
            OpenApiParameter("author", str, description="Trecho do autor (máximo 200 caracteres)."),
            OpenApiParameter("page", int, description="Página, a partir de 1."),
            OpenApiParameter("page_size", int, description="Itens por página, de 1 a 100."),
        ],
        responses={200: BookOutputSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        filters = BookFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        page_size = values.pop("page_size")
        page_number = values.pop("page")
        offset = (page_number - 1) * page_size
        try:
            result = ListBooks(self.repository_class()).execute(
                title=values.get("title"),
                author=values.get("author"),
                offset=offset,
                limit=page_size,
            )
        except InvalidBook as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            _paginated_data(request, result.total, result.items, page_number, page_size)
        )


def _paginated_data(request: Request, total: int, items: list, page: int, page_size: int) -> dict:
    last_item = page * page_size
    return {
        "count": total,
        "next": _page_url(request, page + 1) if last_item < total else None,
        "previous": _page_url(request, page - 1) if page > 1 else None,
        "results": BookOutputSerializer(items, many=True).data,
    }


def _page_url(request: Request, page: int) -> str:
    query = request.query_params.copy()
    query["page"] = page
    return request.build_absolute_uri(f"{reverse('book-list')}?{query.urlencode()}")
