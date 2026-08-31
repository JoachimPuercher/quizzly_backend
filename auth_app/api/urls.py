from django.urls import path
from .views import CookieTokenObtainPairView
from .views import RegistrationView


urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
      path('login/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair')
]


