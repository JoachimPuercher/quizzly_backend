from rest_framework import serializers
from quizzly_app.models import Quiz, Question


class YoutubeUrlSerializer(serializers.Serializer):

    url = serializers.URLField(max_length=500)

    def validate_url(self, value):
        if value.startswith("https://www.youtube.com/watch?v="):
            return value
        else:
            raise serializers.ValidationError("Not a valid youtube URL!")


class QuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question

        fields = [
            'id',
            'question_title',
            'question_options',
            'answer',
            'created_at',
            'updated_at'
        ]



class QuizSerializer(serializers.ModelSerializer):

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
        questions_data = validated_data.pop('questions')
        quiz = Quiz.objects.create(**validated_data)
        for question in questions_data:
            Question.objects.create(quiz=quiz, **question)
        return quiz


class RetrieveQuizSerializer(serializers.ModelSerializer):

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