from rest_framework import serializers

from apps.search.application.use_cases import MAX_QUERY_CHARS, MAX_RESULTS


class QueryField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class CountField(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            self.fail("invalid")
        return super().to_internal_value(data)


class SearchInputSerializer(serializers.Serializer):
    query = QueryField(max_length=MAX_QUERY_CHARS, trim_whitespace=False)
    k = CountField(min_value=1, max_value=MAX_RESULTS, default=5)


class MatchSerializer(serializers.Serializer):
    id = serializers.CharField()
    source = serializers.CharField()
    snippet = serializers.CharField()
    score = serializers.FloatField()
    title = serializers.CharField(allow_blank=True)
    url = serializers.URLField(allow_blank=True)
    metadata = serializers.DictField()


class SearchOutputSerializer(serializers.Serializer):
    results = MatchSerializer(many=True)


class SearchErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
