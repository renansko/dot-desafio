from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.chat.presentation.views import ChatView
from apps.search.presentation.views import SearchView

urlpatterns = [
    path("api/search/", SearchView.as_view(), name="search"),
    path("api/chat/", ChatView.as_view(), name="chat"),
    path("api/", include("apps.library.presentation.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
