from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import RegisterSerializer, UserSerializer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .authentication import JWTCookieAuthentication
from .throttles import AuthRateThrottle


class RegistrationView(generics.CreateAPIView):
    """Register a new user. Open to everyone, rate limited per IP."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = {
            "detail": "User created sucessfully!"
        }

        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """Check the credentials and hand out the tokens as httpOnly cookies.

    Built on the simplejwt view; only the response is changed so that the
    tokens travel in cookies instead of the body.
    """

    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # TokenError is not a DRF exception; translate it into a 401.
            raise InvalidToken(e.args[0]) from e

        response = Response(serializer.validated_data,
                            status=status.HTTP_200_OK)
        access_token = response.data.get("access")
        refresh_token = response.data.get("refresh")

        # Set the tokens as cookies directly on the response. httponly keeps
        # them away from JavaScript, SameSite=Lax stops the browser from
        # sending them with cross-site POST requests (CSRF).
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        # Replace the body so that no token is part of the response.
        response.data = {
            "detail": "Login successfully!",
            "user": UserSerializer(instance=serializer.user).data

        }

        return response


def delete_jwt_cookies(response: Response):
    """Expire both JWT cookies in the browser."""
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/')


class LogoutView(TokenBlacklistView):
    """Blacklist the refresh token and clear both cookies."""

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            serializer = self.get_serializer(data={"refresh": refresh_token})

            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as e:
                raise InvalidToken(e.args[0]) from e

            response = Response(
                {
                    "detail": (
                        "Log-Out successfully! All Tokens will be deleted. "
                        "Refresh token is now invalid."
                    ),
                },
                status=status.HTTP_200_OK,
            )
            delete_jwt_cookies(response)
            return response

        except TokenError:
            # If the token is already invalid/expired, still clear cookies
            response = Response(
                {
                    "detail": (
                        "Log-Out successfully! All Tokens will be deleted. "
                        "Refresh token is now invalid."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
            delete_jwt_cookies(response)
            return response


class CookieTokenRefreshView(TokenRefreshView):
    """Issue a new access token from the refresh cookie."""

    def post(self, request, *args, **kwargs):

        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            return Response(
                {"message": "Refresh token not found!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except:
            return Response(
                {"message": "Refresh token not found!"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        access_token = serializer.validated_data.get("access")
        response = Response({"detail": "Token refreshed."})

        # Same cookie attributes as in LoginView.
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )

        return response
