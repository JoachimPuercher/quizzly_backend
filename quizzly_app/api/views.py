from rest_framework import generics, status
from .serializers import YoutubeUrlSerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from quizzly_app.services.yt_dlp import fetch_youtube
from yt_dlp.utils import DownloadError

class CreateQuizView(generics.CreateAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # return super().post(request, *args, **kwargs)

        url_serializer = YoutubeUrlSerializer(data=request.data)
        url_serializer.is_valid(raise_exception=True)
        youtube_url = url_serializer.validated_data["url"]
        # Extract Audio from YTURL
        try:
            youtube_audio = fetch_youtube(youtube_url)
            print(youtube_audio)
        except DownloadError as e:
            return Response({"detail" : str(e)}, status=status.HTTP_400_BAD_REQUEST)
                    


        # Transcribe Audio to text
        # Create quizzobject with AI

        # Validate Quizzobject with serializer
        # Save object to database
        # Build Response

        return Response(data=url_serializer.validated_data, status=status.HTTP_200_OK)