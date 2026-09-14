from rest_framework.permissions import SAFE_METHODS
from rest_framework.throttling import UserRateThrottle


class QuizCreateRateThrottle(UserRateThrottle):
    """Limit how many quizzes a user may generate.

    Every generation costs minutes of CPU and Gemini quota. The rate is
    configured under the "quiz_create" scope in
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "quiz_create"

    def allow_request(self, request, view):
        # Listing quizzes is cheap, only the generating POST counts.
        if request.method in SAFE_METHODS:
            return True
        return super().allow_request(request, view)
