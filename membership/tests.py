from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import PasswordResetToken


User = get_user_model()

class MembershipViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = reverse('membership:sign-up')
        self.signin_url = reverse('membership:sign-in')
        self.forgot_password_url = reverse('membership:forgot-password')
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpass123',
        }
        self.user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='existingpass123'
        )

    def test_signup_success(self):
        response = self.client.post(self.signup_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_signup_duplicate_username(self):
        data = self.user_data.copy()
        data['username'] = 'existinguser'
        response = self.client.post(self.signup_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_signup_duplicate_email(self):
        data = self.user_data.copy()
        data['email'] = 'existing@example.com'
        response = self.client.post(self.signup_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_forgot_password_success(self):
        response = self.client.post(self.forgot_password_url, {'email': 'existing@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(email='existing@example.com').exists())

    def test_forgot_password_invalid_email(self):
        response = self.client.post(self.forgot_password_url, {'email': 'notfound@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_password_reset_success(self):
        reset = PasswordResetToken.objects.create(email='existing@example.com', token='resettoken123', created_at=timezone.now())
        url = reverse('membership:reset-password')
        response = self.client.post(url, {'token': reset.token, 'new_password': 'newpass456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))
        self.assertFalse(PasswordResetToken.objects.filter(token='resettoken123').exists())

    def test_password_reset_invalid_token(self):
        url = reverse('membership:reset-password')
        response = self.client.post(url, {'token': 'invalidtoken', 'new_password': 'newpass456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)

    def test_password_reset_no_user(self):
        PasswordResetToken.objects.create(email='notfound@example.com', token='othertoken', created_at=timezone.now())
        url = reverse('membership:reset-password')
        response = self.client.post(url, {'token': 'othertoken', 'new_password': 'newpass456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)

class MembershipURLReverseTestCase(TestCase):
    def test_reverse_sign_up(self):
        url = reverse('membership:sign-up')
        self.assertTrue(url.endswith('/api/membership/sign-up/'))

    def test_reverse_sign_in(self):
        url = reverse('membership:sign-in')
        self.assertTrue(url.endswith('/api/membership/sign-in/'))

    def test_reverse_request_password_reset(self):
        url = reverse('membership:forgot-password')
        self.assertTrue(url.endswith('/api/membership/forgot-password/'))

    def test_reverse_password_reset(self):
        url = reverse('membership:password-reset', kwargs={'token': 'sometoken'})
        self.assertTrue(url.endswith('/api/membership/password-reset/sometoken/'))
