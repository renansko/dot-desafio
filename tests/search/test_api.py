from unittest.mock import Mock

import pytest
from rest_framework.test import APIClient

from apps.search.application.errors import SearchTimeout, SearchUnavailable
from apps.search.application.use_cases import Search
from apps.search.infrastructure.faiss_index import FaissIndex


def test_search_http_success(built_index, monkeypatch):
    path, spec, embeddings = built_index
    monkeypatch.setattr("apps.search.presentation.views.create_search", lambda: Search(
        embeddings, FaissIndex(path), spec,
    ))
    response = APIClient().post("/api/search/", {"query": "q", "k": 2}, format="json")
    assert response.status_code == 200
    assert [match["id"] for match in response.data["results"]] == ["a", "b"]
    assert set(response.data["results"][0]) == {
        "id", "source", "snippet", "score", "title", "url", "metadata",
    }


@pytest.mark.parametrize("data", [
    {}, {"query": ""}, {"query": "  "}, {"query": 123}, {"query": None},
    {"query": "a" * 2001}, {"query": "q", "k": 0}, {"query": "q", "k": 21},
    {"query": "q", "k": True}, {"query": "q", "k": "2"}, {"query": "q", "k": 1.0},
    {"query": "q", "k": None}, [],
])
def test_bad_input_before_dependencies(data, monkeypatch):
    factory = Mock(side_effect=AssertionError("dependencies must not be constructed"))
    monkeypatch.setattr("apps.search.presentation.views.create_search", factory)
    assert APIClient().post("/api/search/", data, format="json").status_code == 400
    factory.assert_not_called()


@pytest.mark.parametrize("length,k", [(1999, 1), (2000, 2), (1, 19), (1, 20)])
def test_http_boundaries(length, k, monkeypatch):
    service = Mock()
    service.execute.return_value = []
    monkeypatch.setattr("apps.search.presentation.views.create_search", lambda: service)
    response = APIClient().post("/api/search/", {"query": "x" * length, "k": k}, format="json")
    assert response.status_code == 200


def test_default_count(monkeypatch):
    service = Mock()
    service.execute.return_value = []
    monkeypatch.setattr("apps.search.presentation.views.create_search", lambda: service)
    assert APIClient().post("/api/search/", {"query": "q"}, format="json").status_code == 200
    service.execute.assert_called_once_with(query="q", k=5)


@pytest.mark.parametrize("error,status", [
    (SearchUnavailable("private path"), 503), (SearchTimeout("secret"), 504),
    (RuntimeError("credentials"), 500),
])
def test_safe_errors(error, status, monkeypatch):
    monkeypatch.setattr("apps.search.presentation.views.create_search", Mock(side_effect=error))
    response = APIClient().post("/api/search/", {"query": "q"}, format="json")
    assert response.status_code == status
    assert str(error) not in str(response.data)
    assert set(response.data) == {"detail"}


def test_missing_index_returns_503_without_loading_embeddings():
    response = APIClient().post("/api/search/", {"query": "q"}, format="json")
    assert response.status_code == 503


def test_incompatible_index_http(built_index, monkeypatch):
    path, _, _ = built_index
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(path))
    assert APIClient().post("/api/search/", {"query": "q"}, format="json").status_code == 503


def test_openapi_contract():
    response = APIClient().get("/api/schema/?format=json")
    operation = response.json()["paths"]["/api/search/"]["post"]
    assert set(operation["responses"]) == {"200", "400", "503", "504", "500"}
