from django.urls import path

from apps.library.presentation.views import BookListCreateView

urlpatterns = [path("books/", BookListCreateView.as_view(), name="book-list")]
