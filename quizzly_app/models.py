from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Quiz(models.Model):
    """A quiz generated from a video, holding its questions."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    video_url = models.URLField(max_length=500)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="quizzes", on_delete=models.CASCADE, blank=False)


class Question(models.Model):
    """A single multiple choice question belonging to a quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    question_title = models.CharField(max_length=255)
    question_options = models.JSONField(default=list)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


