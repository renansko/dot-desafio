from dataclasses import asdict

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
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
            200: OpenApiResponse(
                response=SearchOutputSerializer,
                description="Documentos únicos ordenados por relevância.",
                examples=[OpenApiExample("Resultado", value={"results": [{
                    "id": "doc-1", "source": "wikipedia", "snippet": "Modelos aprendem com dados.",
                    "score": 0.82, "title": "Aprendizado de máquina",
                    "url": "https://example.org/doc-1", "metadata": {"language": "pt"},
                }]})],
            ),
            400: OpenApiResponse(
                response=SearchErrorSerializer,
                description="Consulta ou quantidade inválida.",
                examples=[OpenApiExample(
                    "Entrada inválida", value={"detail": "Consulta ou quantidade inválida."},
                )],
            ),
            503: OpenApiResponse(
                response=SearchErrorSerializer,
                description="Índice, modelo ou outra dependência indisponível ou incompatível.",
                examples=[OpenApiExample(
                    "Dependência indisponível", value={"detail": "Dependência indisponível."},
                )],
            ),
            504: OpenApiResponse(
                response=SearchErrorSerializer,
                description="Tempo limite excedido ao acessar dependência externa.",
                examples=[OpenApiExample(
                    "Tempo limite", value={"detail": "Tempo limite da dependência excedido."},
                )],
            ),
            500: OpenApiResponse(
                response=SearchErrorSerializer,
                description="Erro interno inesperado; detalhes internos não são expostos.",
                examples=[OpenApiExample(
                    "Erro interno", value={"detail": "Erro interno do servidor."},
                )],
            ),
        },
        description=(
            "Busca semântica: query não vazia, até 2000 caracteres; k inteiro de 1 a 20 "
            "(padrão 5). Documentos únicos por similaridade cosseno decrescente, com o melhor "
            "trecho. Retorna menos que k quando o corpus tem menos documentos, sem limiar "
            "mínimo de relevância. 503: índice/modelo indisponível ou incompatível; "
            "504: timeout remoto; 500: erro interno."
        ),
        examples=[OpenApiExample(
            "Consulta",
            value={
                "query": "Como explicar decisões tomadas por modelos de machine learning?",
                "k": 2,
            },
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
