from rest_framework.authtoken.views import obtain_auth_token
from django.urls import path
from .views import ForgotPasswordView, ResetPasswordView, SignUpView

app_name = "membership"

urlpatterns = [
    path('sign-in/', obtain_auth_token, name='sign-in'),
    path('sign-up/', SignUpView.as_view(), name='sign-up'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]
