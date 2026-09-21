from dataclasses import asdict

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.application.errors import InvalidSearch
from apps.search.application.use_cases import Search, validate_query
from apps.search.infrastructure.embeddings import LangChainEmbeddings
from apps.search.infrastructure.faiss_index import FaissIndex
from apps.search.infrastructure.settings import load_config
from apps.search.presentation.serializers import (
    SearchErrorSerializer,
    SearchInputSerializer,
    SearchOutputSerializer,
)


def create_search():
    config = load_config()
    return Search(LangChainEmbeddings(config), FaissIndex(config.path), config.spec)


class SearchView(APIView):
    @extend_schema(
        request=SearchInputSerializer,
        responses={
            200: SearchOutputSerializer, 400: SearchErrorSerializer,
            503: SearchErrorSerializer, 504: SearchErrorSerializer, 500: SearchErrorSerializer,
        },
        description=(
            "Busca semântica: query não vazia, até 2000 caracteres; k inteiro de 1 a 20 "
            "(padrão 5). Documentos únicos por similaridade cosseno decrescente, com o melhor "
            "trecho. Retorna menos que k quando o corpus tem menos documentos, sem limiar "
            "mínimo de relevância. 503: índice/modelo indisponível ou incompatível; "
            "504: timeout remoto; 500: erro interno."
        ),
        examples=[OpenApiExample(
            "Consulta", value={"query": "Como guardar dinheiro para imprevistos?", "k": 2},
            request_only=True,
        )],
    )
    def post(self, request):
        serializer = SearchInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Consulta ou quantidade inválida."}, status=400)
        values = serializer.validated_data
        try:
            validate_query(values["query"], values["k"])
            matches = create_search().execute(**values)
        except InvalidSearch as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"results": [asdict(match) for match in matches]})
