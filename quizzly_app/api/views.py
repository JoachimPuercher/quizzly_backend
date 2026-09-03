from rest_framework import generics, status
from .serializers import YoutubeUrlSerializer, QuizSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from quizzly_app.services.yt_dlp import fetch_youtube
from yt_dlp.utils import DownloadError
from quizzly_app.services.transcribe import transcribe_audio_to_text
from quizzly_app.services.gemini import create_quiz

class CreateQuizView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        url_serializer = YoutubeUrlSerializer(data=request.data)
        url_serializer.is_valid(raise_exception=True)
        youtube_url = url_serializer.validated_data["url"]

        try:
            youtube_audio = fetch_youtube(youtube_url)
        except DownloadError as e:
            return Response({"detail" : str(e)}, status=status.HTTP_400_BAD_REQUEST)
                    
        try:
            video_text = transcribe_audio_to_text(youtube_audio)
        except Exception as e:
            print(f"TRANSCRIBE ERROR: {type(e).__name__}: {e}")
            return Response({"detail" : "Audio to text transcribtion failed!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quiz_data = create_quiz(video_text).model_dump()
        except Exception as e:
            return Response(data={{type(e).__name__}: {e}}, status=status.HTTP_200_OK)

        quiz_serializer = QuizSerializer(data=quiz_data)
        quiz_serializer.is_valid(raise_exception=True)
        quiz_serializer.save(video_url=youtube_url, owner=request.user)

        return Response(data=quiz_serializer.data, status=status.HTTP_201_CREATED)
