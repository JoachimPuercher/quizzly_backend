from rest_framework_simplejwt.authentication import JWTAuthentication, JWTTokenUserAuthentication
from typing import Optional, TypeVar

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING, authentication
from rest_framework.request import Request


from rest_framework_simplejwt.tokens import Token, AuthUser

class JWTCookieAuthentication(JWTAuthentication):

    def authenticate(self, request: Request) -> Optional[tuple[AuthUser, Token]]:
       
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
    
class JWTCookieRefreshAuthentication(JWTAuthentication):

    def authenticate(self, request: Request) -> Optional[tuple[AuthUser, Token]]:
       
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
    