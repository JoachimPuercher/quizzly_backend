from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Limit login and registration attempts per IP address."""

    scope = "auth"
