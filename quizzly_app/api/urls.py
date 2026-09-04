from django.urls import path

from .views import CreateQuizView, RetrieveUpdateDestroyQuizView


urlpatterns = [
    path('quizzes/', CreateQuizView.as_view(), name="quizzes"),
    path(
        'quizzes/<int:id>/',
        RetrieveUpdateDestroyQuizView.as_view(),
        name="quiz_detail",
    ),
]
