import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quizzly_app.models import Quiz
from quizzly_app.services.gemini import create_quiz
from quizzly_app.services.transcribe import transcribe_audio_to_text
from quizzly_app.services.yt_dlp import (
    VideoTooLongError,
    fetch_youtube,
    remove_download,
)

from .permissions import IsQuizOwner
from .serializers import (
    QuizSerializer,
    RetrieveQuizSerializer,
    UpdateQuizSerializer,
    YoutubeUrlSerializer,
)
from .throttles import QuizCreateRateThrottle

logger = logging.getLogger(__name__)


class CreateQuizView(generics.ListCreateAPIView):
    """List the quizzes of the current user and create new ones."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [QuizCreateRateThrottle]
    # Describes the POST body for OPTIONS and the browsable API.
    serializer_class = YoutubeUrlSerializer

    def get_queryset(self):
        return Quiz.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        """Return only the quizzes owned by the requesting user."""
        serializer = RetrieveQuizSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Download, transcribe and turn a YouTube video into a quiz."""
        url_serializer = self.get_serializer(data=request.data)
        url_serializer.is_valid(raise_exception=True)
        youtube_url = url_serializer.validated_data["url"]

        try:
            audio_path = fetch_youtube(youtube_url)
        except VideoTooLongError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DownloadError as e:
            # The yt-dlp message may contain internal details, log only.
            logger.warning("Download failed for %s: %s", youtube_url, e)
            return Response(
                {"detail": "The video could not be downloaded."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            video_text = transcribe_audio_to_text(audio_path)
        except Exception:
            logger.exception("Transcription failed for %s", youtube_url)
            return Response(
                {"detail": "Transcription failed, please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            # The audio file is only needed for the transcription.
            remove_download(audio_path)

        try:
            quiz_data = create_quiz(video_text).model_dump()
        except Exception:
            logger.exception("Quiz generation failed for %s", youtube_url)
            return Response(
                {"detail": "Quiz generation failed, please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        quiz_serializer = QuizSerializer(data=quiz_data)
        quiz_serializer.is_valid(raise_exception=True)
        quiz_serializer.save(video_url=youtube_url, owner=request.user)

        return Response(quiz_serializer.data, status=status.HTTP_201_CREATED)


class RetrieveUpdateDestroyQuizView(generics.RetrieveUpdateDestroyAPIView):
    """Read, patch or delete a single quiz of the current user."""

    # The API documentation asks for 403 on a foreign quiz and 404 on an
    # unknown id, so the queryset is not filtered and IsQuizOwner decides.
    permission_classes = [IsAuthenticated, IsQuizOwner]
    queryset = Quiz.objects.all()
    # PUT would need the nested questions to be writable, so only PATCH.
    http_method_names = ["get", "patch", "delete", "head", "options"]
    lookup_url_kwarg = "id"

    def get_serializer_class(self):
        """Use the restricted serializer for writes, the full one for reads."""
        if self.request.method == "PATCH":
            return UpdateQuizSerializer
        return RetrieveQuizSerializer
