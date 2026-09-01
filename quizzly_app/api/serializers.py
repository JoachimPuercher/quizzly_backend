from rest_framework import serializers


class YoutubeUrlSerializer(serializers.Serializer):

    url = serializers.URLField(max_length=500)

    def validate_url(self, value):
        if value.startswith("https://www.youtube.com/watch?v="):
            return value
        else:
            raise serializers.ValidationError("Not a valid youtube URL!")