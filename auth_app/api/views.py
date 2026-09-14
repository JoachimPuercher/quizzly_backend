from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .serializers import RegisterSerializer, UserSerializer
from .throttles import AuthRateThrottle


def delete_jwt_cookies(response):
    """Expire both JWT cookies in the browser."""
    response.delete_cookie("access_token", path="/", samesite="Lax")
    response.delete_cookie("refresh_token", path="/", samesite="Lax")


class RegistrationView(generics.CreateAPIView):
    """Register a new user. Open to everyone, rate limited per IP."""

    # A stale access cookie must not get in the way of registering.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Check the credentials and hand out the tokens as httpOnly cookies."""

    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # TokenError is not a DRF exception; translate it into a 401.
            raise InvalidToken(e.args[0]) from e

        response = Response(
            {
                "detail": "Login successfully!",
                "user": UserSerializer(serializer.user).data,
            },
            status=status.HTTP_200_OK,
        )
        # httponly keeps the cookies away from JavaScript, SameSite=Lax stops
        # the browser from sending them with cross-site POST requests (CSRF),
        # secure means HTTPS only (browsers treat localhost as secure too),
        # max_age lets the cookie expire together with its token.
        response.set_cookie(
            key="access_token",
            value=serializer.validated_data["access"],
            max_age=api_settings.ACCESS_TOKEN_LIFETIME,
            httponly=True,
            secure=True,
            samesite="Lax",
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=serializer.validated_data["refresh"],
            max_age=api_settings.REFRESH_TOKEN_LIFETIME,
            httponly=True,
            secure=True,
            samesite="Lax",
            path="/",
        )
        return response


class LogoutView(TokenBlacklistView):
    """Blacklist the refresh token and clear both cookies.

    Only the refresh cookie is needed, so logging out still works after
    the short lived access token has expired. The cookies are cleared in
    every case, because a token the server rejects is of no use in the
    browser either.
    """

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token is None:
            response = Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            delete_jwt_cookies(response)
            return response

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            response = Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            delete_jwt_cookies(response)
            return response

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


class CookieTokenRefreshView(TokenRefreshView):
    """Issue a new access token from the refresh cookie."""

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token is None:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        response = Response(
            {"detail": "Token refreshed"},
            status=status.HTTP_200_OK,
        )
        # Same attributes as in LoginView.
        response.set_cookie(
            key="access_token",
            value=serializer.validated_data["access"],
            max_age=api_settings.ACCESS_TOKEN_LIFETIME,
            httponly=True,
            secure=True,
            samesite="Lax",
            path="/",
        )
        return response
