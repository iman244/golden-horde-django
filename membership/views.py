import os
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework import generics, status, mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import PasswordResetToken
from .serializers import CreateUserSerializer, ForgotPasswordSerializer, ResetPasswordSerializer

User = get_user_model()


class SignUpView(mixins.CreateModelMixin, generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer

    def post(self, request, *args, **kwargs):
        try:
            username = request.data.get("username")
            if User.objects.filter(username=username).exists():
                return Response({
                    "username": ["A user with this username is already signed up"]
                }, status=status.HTTP_400_BAD_REQUEST)
            email = request.data.get("email")
            if User.objects.filter(email=email).exists():
                return Response({
                    "email": ["A user with this email is already signed up"]
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self.create(request, *args, **kwargs)


class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "User with this email not found"}, status=status.HTTP_404_NOT_FOUND)

        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        reset = PasswordResetToken(
            email=email, token=token)
        reset.save()

        front_auth_reset_password_url = 'auth/reset-password'

        reset_url = f"{os.environ['FRONTEND_URL']}/{front_auth_reset_password_url}/{token}"

        send_mail(
            "Golden Horde - request for reset password",
            f"Dear {user.username}\nyou can reset your password using this url {reset_url}",
            from_email=os.environ['EMAIL_HOST_USER'],
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({'message': 'We have sent you an email containing a link for password reset '}, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token = data.get('token')
        new_password = data['new_password']

        reset_obj = PasswordResetToken.objects.filter(token=token).first()

        if not reset_obj:
            return Response({'message': 'Token not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if token is expired
        if reset_obj.is_expired():
            reset_obj.delete()
            return Response({'message': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=reset_obj.email)
        except User.DoesNotExist:
            reset_obj.delete()
            return Response({'message': 'No user found'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()
        reset_obj.delete()

        return Response({'message': 'Password updated'}, status=status.HTTP_200_OK)
