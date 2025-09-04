from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
import json


class AuthAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_register_success(self):
        """Test successful user registration"""
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = self.client.post('/api/auth/register/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        
        # Check user was created in database
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_register_duplicate_username(self):
        """Test registration with duplicate username fails"""
        User.objects.create_user(username='testuser', password='pass123')
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/auth/register/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields"""
        data = {'username': 'testuser'}  # Missing password
        
        response = self.client.post('/api/auth/register/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_success(self):
        """Test successful login"""
        user = User.objects.create_user(username='testuser', password='testpass123')
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/auth/login/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        User.objects.create_user(username='testuser', password='testpass123')
        
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post('/api/auth/login/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        data = {'username': 'testuser'}  # Missing password
        
        response = self.client.post('/api/auth/login/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_profile_authenticated(self):
        """Test profile endpoint with authentication"""
        user = User.objects.create_user(username='testuser', password='testpass123')
        
        # Login to get token
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        login_response = self.client.post('/api/auth/login/', login_data, format='json')
        access_token = login_response.data['access']
        
        # Access profile with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_profile_unauthenticated(self):
        """Test profile endpoint without authentication"""
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
