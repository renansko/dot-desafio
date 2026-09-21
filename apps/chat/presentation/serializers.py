from rest_framework import serializers


class TextField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class HistoryMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = TextField(allow_blank=False, trim_whitespace=False)


class ChatInputSerializer(serializers.Serializer):
    question = TextField(allow_blank=False, trim_whitespace=False)
    history = HistoryMessageSerializer(many=True, required=False, default=list)


class ChatOutputSerializer(serializers.Serializer):
    answer = serializers.CharField()


class ChatErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
