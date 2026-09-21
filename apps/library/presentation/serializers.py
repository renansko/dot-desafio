from rest_framework import serializers

from apps.library.application.use_cases import (
    AUTHOR_MAX_LENGTH,
    FILTER_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)


class StrictCharField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class BookInputSerializer(serializers.Serializer):
    title = StrictCharField(max_length=TITLE_MAX_LENGTH, allow_blank=False, trim_whitespace=True)
    author = StrictCharField(max_length=AUTHOR_MAX_LENGTH, allow_blank=False, trim_whitespace=True)
    publication_date = serializers.DateField()
    summary = StrictCharField(
        max_length=SUMMARY_MAX_LENGTH, allow_blank=False, trim_whitespace=True
    )


class BookOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    author = serializers.CharField()
    publication_date = serializers.DateField()
    summary = serializers.CharField()


class BookFilterSerializer(serializers.Serializer):
    title = StrictCharField(
        max_length=FILTER_MAX_LENGTH, required=False, allow_blank=False, trim_whitespace=True
    )
    author = StrictCharField(
        max_length=FILTER_MAX_LENGTH, required=False, allow_blank=False, trim_whitespace=True
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False, default=20)
