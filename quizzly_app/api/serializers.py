from rest_framework import serializers

from quizzly_app.models import Quiz, Question


class YoutubeUrlSerializer(serializers.Serializer):
    """Validate the YouTube URL a quiz is generated from."""

    url = serializers.URLField(max_length=500)

    def validate_url(self, value):
        # Only the desktop watch URL is supported; the fixed host also
        # rules out SSRF.
        if value.startswith("https://www.youtube.com/watch?v="):
            return value
        else:
            raise serializers.ValidationError("Not a valid youtube URL!")


class QuestionSerializer(serializers.ModelSerializer):
    """A single question, used nested inside the quiz serializers."""

    class Meta:
        model = Question
        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at',
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Write serializer that stores a quiz together with its questions."""

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
        read_only_fields = ['video_url']

    def create(self, validated_data):
        # Nested writes are not supported by default, so create both levels.
        questions_data = validated_data.pop('questions')
        quiz = Quiz.objects.create(**validated_data)
        for question in questions_data:
            Question.objects.create(quiz=quiz, **question)
        return quiz


class RetrieveQuizSerializer(serializers.ModelSerializer):
    """Read serializer returning a quiz with all of its questions."""

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
        read_only_fields = ['video_url']


class UpdateQuizSerializer(serializers.ModelSerializer):
    """Update serializer that limits writes to title and description."""

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]
