from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quizzly_app.models import Quiz, Question


def create_quiz(owner, title="Test Quiz"):
    """Create a quiz with a single question for the given owner."""
    quiz = Quiz.objects.create(
        title=title,
        description="A quiz used in the tests.",
        video_url="https://www.youtube.com/watch?v=abcdefghijk",
        owner=owner,
    )
    Question.objects.create(
        quiz=quiz,
        question_title="What is 2 + 2?",
        question_options=["1", "2", "3", "4"],
        answer="4",
    )
    return quiz


class QuizListTests(APITestCase):
    """Cover the list endpoint under quizzes/."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")
        self.quiz = create_quiz(self.owner)
        create_quiz(self.other, title="Foreign Quiz")

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_quizzes(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Quiz")


class QuizDetailTests(APITestCase):
    """Cover retrieve, update and destroy under quizzes/<id>/."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")
        self.quiz = create_quiz(self.owner)
        self.url = reverse('quiz_detail', kwargs={"id": self.quiz.id})

    def test_owner_can_retrieve_quiz_with_questions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 1)

    def test_foreign_user_cannot_retrieve_quiz(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_patch_title(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(self.url, {"title": "New Title"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "New Title")

    def test_owner_can_delete_quiz_and_its_questions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(pk=self.quiz.pk).exists())
        self.assertFalse(Question.objects.filter(quiz_id=self.quiz.pk).exists())
