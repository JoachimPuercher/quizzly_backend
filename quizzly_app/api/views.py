from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quizzly_app.models import Quiz
from quizzly_app.services.gemini import create_quiz
from quizzly_app.services.transcribe import transcribe_audio_to_text
from quizzly_app.services.yt_dlp import fetch_youtube

from .permissions import IsQuizOwner
from .serializers import (
    QuizSerializer,
    RetrieveQuizSerializer,
    UpdateQuizSerializer,
    YoutubeUrlSerializer,
)
from .throttles import QuizCreateRateThrottle


class CreateQuizView(generics.ListCreateAPIView):
    """List the quizzes of the current user and create new ones."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [QuizCreateRateThrottle]
    # Describes the POST body for OPTIONS and the browsable API.
    serializer_class = YoutubeUrlSerializer

    def post(self, request, *args, **kwargs):
        """Download, transcribe and turn a YouTube video into a stored quiz."""
        url_serializer = YoutubeUrlSerializer(data=request.data)
        url_serializer.is_valid(raise_exception=True)
        youtube_url = url_serializer.validated_data["url"]

        try:
            youtube_audio = fetch_youtube(youtube_url)
        except DownloadError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            video_text = transcribe_audio_to_text(youtube_audio)
        except Exception as e:
            return Response(
                {"detail": "Audio to text transcribtion failed!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quiz_data = create_quiz(video_text).model_dump()
        except Exception as e:
            return Response(
                {"detail": "Quiz generation failed!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quiz_serializer = QuizSerializer(data=quiz_data)
        quiz_serializer.is_valid(raise_exception=True)
        quiz_serializer.save(video_url=youtube_url, owner=request.user)

        return Response(
            data=quiz_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        """Return only the quizzes owned by the requesting user."""
        queryset = Quiz.objects.filter(owner=request.user)
        serializer = RetrieveQuizSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveUpdateDestroyQuizView(generics.RetrieveUpdateDestroyAPIView):
    """Read, update or delete a single quiz addressed by its id."""

    permission_classes = [IsAuthenticated, IsQuizOwner]
    queryset = Quiz.objects.all()
    # PUT would need the nested questions to be writable, so only PATCH.
    http_method_names = ["get", "patch", "delete", "head", "options"]
    lookup_field = "pk"
    lookup_url_kwarg = "id"

    def get_serializer_class(self):
        """Use the restricted serializer for writes, the full one for reads."""
        if self.request.method == "PATCH":
            return UpdateQuizSerializer
        else:
            return RetrieveQuizSerializer
