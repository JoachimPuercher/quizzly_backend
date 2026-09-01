from django.urls import path
from .views import CreateQuizView


urlpatterns = [
    path('quizzes/', CreateQuizView.as_view(), name="create_quiz")
]


