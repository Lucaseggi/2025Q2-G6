from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertIn('message', response.data)