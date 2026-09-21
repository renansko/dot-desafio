import pytest
from django.db import OperationalError
from rest_framework.test import APIClient

from apps.library.application.errors import ExternalTimeout
from apps.library.models import BookRecord
from apps.library.presentation.views import BookListCreateView


@pytest.fixture
def client():
    return APIClient()


def payload(**changes):
    values = {
        "title": "Python em prática",
        "author": "Ana Silva",
        "publication_date": "2024-01-15",
        "summary": "Introdução prática.",
    }
    values.update(changes)
    return values


@pytest.mark.django_db
def test_post_creates_book_and_returns_it(client):
    response = client.post("/api/books/", payload(), format="json")

    assert response.status_code == 201
    assert response.data["id"] == BookRecord.objects.get().id
    assert response.data["title"] == "Python em prática"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"title": ""}, "title"),
        ({"author": "   "}, "author"),
        ({"summary": ""}, "summary"),
        ({"publication_date": "31/31/2024"}, "publication_date"),
        ({"title": 123}, "title"),
        ({"summary": "x" * 5_001}, "summary"),
    ],
)
def test_post_rejects_invalid_input(client, changes, field):
    response = client.post("/api/books/", payload(**changes), format="json")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.django_db
def test_post_rejects_missing_required_field(client):
    values = payload()
    values.pop("author")

    response = client.post("/api/books/", values, format="json")

    assert response.status_code == 400
    assert "author" in response.data


@pytest.mark.django_db
def test_get_combines_case_insensitive_partial_filters(client):
    BookRecord.objects.create(**payload(title="Python Essencial", author="Ana Souza"))
    BookRecord.objects.create(**payload(title="Python Web", author="Bruno Lima"))
    BookRecord.objects.create(**payload(title="Django", author="Ana Souza"))

    response = client.get("/api/books/", {"title": "PYth", "author": "ANA"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert [item["title"] for item in response.data["results"]] == ["Python Essencial"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "expected"),
    [({"title": "django"}, ["Django"]), ({"author": "bruno"}, ["Python Web"])],
)
def test_get_filters_individually(client, query, expected):
    BookRecord.objects.create(**payload(title="Django", author="Ana"))
    BookRecord.objects.create(**payload(title="Python Web", author="Bruno"))

    response = client.get("/api/books/", query)

    assert [item["title"] for item in response.data["results"]] == expected


@pytest.mark.django_db
def test_get_lists_empty_result(client):
    response = client.get("/api/books/", {"title": "ausente"})

    assert response.status_code == 200
    assert response.data == {"count": 0, "next": None, "previous": None, "results": []}


@pytest.mark.django_db
def test_get_paginates_and_preserves_filters_in_links(client):
    for index in range(3):
        BookRecord.objects.create(**payload(title=f"Python {index}"))

    response = client.get("/api/books/", {"title": "python", "page": 2, "page_size": 1})

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert response.data["results"][0]["title"] == "Python 1"
    assert "title=python" in response.data["previous"]
    assert "page=3" in response.data["next"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query", [{"page": 0}, {"page": "x"}, {"page_size": 0}, {"page_size": 101}]
)
def test_get_rejects_invalid_pagination(client, query):
    assert client.get("/api/books/", query).status_code == 400


@pytest.mark.django_db
def test_dependency_error_has_safe_503_response(client, monkeypatch):
    monkeypatch.setattr(
        BookRecord.objects, "create", lambda **kwargs: (_ for _ in ()).throw(OperationalError())
    )

    response = client.post("/api/books/", payload(), format="json")

    assert response.status_code == 503
    assert response.data == {"detail": "Dependência indisponível."}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (ExternalTimeout(), 504, "Tempo limite da dependência excedido."),
        (RuntimeError("internal details"), 500, "Erro interno do servidor."),
    ],
)
def test_unhandled_errors_have_safe_standard_responses(
    client, monkeypatch, error, expected_status, expected_detail
):
    class FailingRepository:
        def __init__(self):
            raise error

    monkeypatch.setattr(BookListCreateView, "repository_class", FailingRepository)

    response = client.get("/api/books/")

    assert response.status_code == expected_status
    assert response.data == {"detail": expected_detail}
    assert "internal details" not in str(response.data)


@pytest.mark.django_db
def test_schema_is_available_and_documents_limits(client):
    response = client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    schema = response.json()
    assert (
        schema["components"]["schemas"]["BookInput"]["properties"]["summary"]["maxLength"] == 5_000
    )
    parameters = schema["paths"]["/api/books/"]["get"]["parameters"]
    assert {item["name"] for item in parameters} >= {"title", "author", "page", "page_size"}


def test_swagger_ui_is_available(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert "text/html" in response["content-type"]
    assert b"swagger-ui" in response.content.lower()
