from typing import Optional

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AuthUser, Token


class JWTCookieAuthentication(JWTAuthentication):
    """Authenticate from the httpOnly access_token cookie.

    The browser attaches the cookie on its own, so cross-site request
    forgery is only held off by the SameSite=Lax attribute set in
    auth_app.api.views. That is enough as long as the frontend and this
    API are served from the same site.
    """

    def authenticate(
        self, request: Request
    ) -> Optional[tuple[AuthUser, Token]]:
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            # No cookie means anonymous; the permission classes decide.
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
