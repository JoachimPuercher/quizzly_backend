from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .authentication import JWTCookieAuthentication
from .throttles import AuthRateThrottle



# 100% WORKING - NORMAL TOKEN AUTH.
class RegistrationView(generics.CreateAPIView):
    """Registers a new user and returns the auth token right away."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = {
            "detail" : "User created sucessfully!"
        }

        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
# Self created class from the simplejwt class.
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        access_token = response.data.get("access")
        refresh_token =response.data.get("refresh")

        # Set cookie direkt on response access/token.
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
        # Update response.data that no access/refresh token is in the response.
        response.data = {
            "detail" : "Login successfully!",
            "user" : UserSerializer(instance=serializer.user).data

            }

        return response

def delete_jwt_cookies(response:Response):
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/')

class LogoutView(TokenBlacklistView):

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:

        print(request.COOKIES)
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            serializer = self.get_serializer(data={"refresh" : refresh_token})

            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as e:
                raise InvalidToken(e.args[0]) from e

            response = Response({"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}, status=status.HTTP_200_OK)
            delete_jwt_cookies(response)
            return response

        except TokenError:
            # If the token is already invalid/expired, still clear cookies
            response = Response({"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}, status=status.HTTP_400_BAD_REQUEST)
            delete_jwt_cookies(response)
            return response

class CookieTokenRefreshView(TokenRefreshView):
    

    def post(self, request, *args, **kwargs):

        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            return Response(
                {"message" : "Refresh token not found!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data={"refresh":refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except:
            return Response(
                {"message" : "Refresh token not found!"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        access_token = serializer.validated_data.get("access")
        response = Response({"detail" : "Token refreshed."})

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )

        return response