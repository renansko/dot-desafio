from django.db import models


class BookRecord(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    publication_date = models.DateField()
    summary = models.TextField(max_length=5_000)

    class Meta:
        ordering = ["id"]
