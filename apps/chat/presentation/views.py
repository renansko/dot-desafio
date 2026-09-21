from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.application.errors import InvalidChat
from apps.chat.application.use_cases import AskPython, Message
from apps.chat.infrastructure.providers import create_provider
from apps.chat.infrastructure.settings import load_limits
from apps.chat.presentation.serializers import (
    ChatErrorSerializer,
    ChatInputSerializer,
    ChatOutputSerializer,
)


class ChatView(APIView):
    @extend_schema(
        request=ChatInputSerializer,
        responses={
            200: ChatOutputSerializer,
            400: ChatErrorSerializer,
            503: ChatErrorSerializer,
            504: ChatErrorSerializer,
            500: ChatErrorSerializer,
        },
        description=(
            "Chat Python sem persistência. Limites padrão: pergunta/mensagem 4000 caracteres, "
            "20 mensagens e 16000 caracteres totais; configuráveis por CHAT_MAX_*. "
            "400: entrada inválida; 503: configuração/provedor indisponível; "
            "504: timeout; 500: erro interno."
        ),
        examples=[
            OpenApiExample(
                "Pergunta inicial",
                request_only=True,
                value={"question": "Como criar uma lista em Python?"},
            )
        ],
    )
    def post(self, request):
        serializer = ChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Pergunta ou histórico inválido."}, status=400)
        values = serializer.validated_data
        history = [Message(**message) for message in values["history"]]
        try:
            answer = AskPython(LazyProvider(), load_limits()).execute(values["question"], history)
        except InvalidChat as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"answer": answer})


class LazyProvider:
    def answer(self, system, messages):
        # Validate input before requiring credentials or constructing any external client.
        return create_provider().answer(system, messages)
