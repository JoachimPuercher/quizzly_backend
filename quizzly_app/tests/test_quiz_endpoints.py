import os
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from yt_dlp.utils import DownloadError

from quizzly_app.models import Quiz, Question
from quizzly_app.services.yt_dlp import VideoTooLongError

YOUTUBE_URL = "https://www.youtube.com/watch?v=abcdefghijk"
VIEWS = "quizzly_app.api.views"


def create_quiz(owner, title="Test Quiz"):
    """Create a quiz with a single question for the given owner."""
    quiz = Quiz.objects.create(
        title=title,
        description="A quiz used in the tests.",
        video_url=YOUTUBE_URL,
        owner=owner,
    )
    Question.objects.create(
        quiz=quiz,
        question_title="What is 2 + 2?",
        question_options=["1", "2", "3", "4"],
        answer="4",
    )
    return quiz


def generated_quiz(question_count=10):
    """The dict the Gemini service would return for a generated quiz."""
    return {
        "title": "Generated Quiz",
        "description": "Generated from a transcript.",
        "questions": [
            {
                "question_title": f"Question {number}?",
                "question_options": ["A", "B", "C", "D"],
                "answer": "A",
            }
            for number in range(question_count)
        ],
    }


class QuizListTests(APITestCase):
    """Cover the list endpoint under quizzes/."""

    def setUp(self):
        cache.clear()
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

    def test_options_describes_the_endpoint(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.options(reverse('quizzes'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class QuizCreateTests(APITestCase):
    """Cover POST quizzes/ with the three services mocked."""

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.client.force_authenticate(user=self.owner)
        # A real temporary file stands in for the downloaded audio.
        handle = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        handle.close()
        self.audio_path = handle.name
        self.addCleanup(self.remove_audio)

    def remove_audio(self):
        if os.path.exists(self.audio_path):
            os.remove(self.audio_path)

    def post_quiz(self, fetch=None, transcribe=None, generate=None):
        """Post the URL with the three services replaced by mocks."""
        self.fetch = fetch or Mock(return_value=self.audio_path)
        self.transcribe = transcribe or Mock(return_value="transcript")
        generated = Mock(model_dump=Mock(return_value=generated_quiz()))
        self.generate = generate or Mock(return_value=generated)
        with (
            patch(f"{VIEWS}.fetch_youtube", self.fetch),
            patch(f"{VIEWS}.transcribe_audio_to_text", self.transcribe),
            patch(f"{VIEWS}.create_quiz", self.generate),
        ):
            return self.client.post(reverse('quizzes'), {"url": YOUTUBE_URL})

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.post_quiz()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.fetch.assert_not_called()

    def test_create_rejects_invalid_url(self):
        self.fetch = Mock()
        with patch(f"{VIEWS}.fetch_youtube", self.fetch):
            response = self.client.post(
                reverse('quizzes'), {"url": "https://vimeo.com/1"}
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.fetch.assert_not_called()

    def test_create_returns_400_when_download_fails(self):
        error = DownloadError("internal detail")
        with self.assertLogs(VIEWS, level="WARNING") as logs:
            response = self.post_quiz(fetch=Mock(side_effect=error))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # the raw yt-dlp message goes to the log, not to the client
        self.assertNotIn("internal detail", response.data["detail"])
        self.assertIn("internal detail", logs.output[0])
        self.transcribe.assert_not_called()

    def test_create_returns_400_for_too_long_video(self):
        error = VideoTooLongError("too long")

        response = self.post_quiz(fetch=Mock(side_effect=error))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.transcribe.assert_not_called()

    def test_create_returns_502_when_transcription_fails(self):
        error = RuntimeError("whisper")
        with self.assertLogs(VIEWS, level="ERROR"):
            response = self.post_quiz(transcribe=Mock(side_effect=error))

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.generate.assert_not_called()
        # the audio file is removed even when the transcription fails
        self.assertFalse(os.path.exists(self.audio_path))

    def test_create_returns_502_when_generation_fails(self):
        error = RuntimeError("gemini")
        with self.assertLogs(VIEWS, level="ERROR"):
            response = self.post_quiz(generate=Mock(side_effect=error))

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(Quiz.objects.count(), 0)

    def test_create_stores_quiz_with_questions(self):
        response = self.post_quiz()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["questions"]), 10)

        quiz = Quiz.objects.get()
        self.assertEqual(quiz.owner, self.owner)
        self.assertEqual(quiz.video_url, YOUTUBE_URL)
        self.assertEqual(quiz.questions.count(), 10)

        self.fetch.assert_called_once_with(YOUTUBE_URL)
        self.transcribe.assert_called_once_with(self.audio_path)
        self.generate.assert_called_once_with("transcript")
        # the downloaded audio is removed once it has been transcribed
        self.assertFalse(os.path.exists(self.audio_path))

    def test_create_is_throttled(self):
        for _ in range(5):
            open(self.audio_path, "w").close()
            response = self.post_quiz()
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.post_quiz()

        self.assertEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )
        self.assertEqual(Quiz.objects.count(), 5)


class QuizDetailTests(APITestCase):
    """Cover retrieve, update and destroy under quizzes/<id>/."""

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")
        self.quiz = create_quiz(self.owner)
        self.url = reverse('quiz_detail', kwargs={"id": self.quiz.id})

    def test_detail_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_retrieve_quiz_with_questions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 1)

    def test_unknown_quiz_is_not_found(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse('quiz_detail', kwargs={"id": 999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_foreign_quiz_is_forbidden(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_foreign_user_cannot_patch_quiz(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(self.url, {"title": "Hijacked"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "Test Quiz")

    def test_foreign_user_cannot_delete_quiz(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(pk=self.quiz.pk).exists())

    def test_owner_can_patch_title(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(self.url, {"title": "New Title"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "New Title")

    def test_patch_ignores_video_url_and_questions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.url,
            {
                "video_url": "https://www.youtube.com/watch?v=other",
                "questions": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.video_url, YOUTUBE_URL)
        self.assertEqual(self.quiz.questions.count(), 1)

    def test_put_is_not_allowed(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(self.url, {"title": "Replaced"})

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_owner_can_delete_quiz_and_its_questions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(pk=self.quiz.pk).exists())
        self.assertFalse(
            Question.objects.filter(quiz_id=self.quiz.pk).exists()
        )
