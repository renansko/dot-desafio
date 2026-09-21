import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.chat.application.errors import ChatTimeout, ChatUnavailable
from apps.library.application.errors import DependencyUnavailable, ExternalTimeout
from apps.search.application.errors import SearchTimeout, SearchUnavailable

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    if isinstance(exc, (DependencyUnavailable, ChatUnavailable, SearchUnavailable)):
        return Response({"detail": "Dependência indisponível."}, status=503)
    if isinstance(exc, (ExternalTimeout, ChatTimeout, SearchTimeout)):
        return Response({"detail": "Tempo limite da dependência excedido."}, status=504)
    logger.exception("Unexpected API error", exc_info=exc)
    return Response({"detail": "Erro interno do servidor."}, status=500)
