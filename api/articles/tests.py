from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from .models import Question
import json


class QuestionAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        
        # Login to get access token
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        login_response = self.client.post('/api/auth/login/', login_data, format='json')
        self.access_token = login_response.data['access']
        
        # Set authorization header for authenticated requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_create_question_success(self):
        """Test successful question creation"""
        data = {
            'question': 'What are the constitutional rights in Argentina?'
        }
        
        response = self.client.post('/api/questions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['question_text'], data['question'])
        self.assertIn('answer_text', response.data)
        self.assertIn('processing_time', response.data)
        self.assertEqual(response.data['user'], 'testuser')
        
        # Check question was created in database
        self.assertTrue(Question.objects.filter(question_text=data['question']).exists())
    
    def test_create_question_missing_text(self):
        """Test question creation without question text"""
        data = {}  # Missing question
        
        response = self.client.post('/api/questions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_question_empty_text(self):
        """Test question creation with empty question text"""
        data = {'question': ''}
        
        response = self.client.post('/api/questions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_question_unauthenticated(self):
        """Test question creation without authentication"""
        # Remove authentication
        self.client.credentials()
        
        data = {
            'question': 'What are the constitutional rights in Argentina?'
        }
        
        response = self.client.post('/api/questions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_questions_authenticated(self):
        """Test listing user's questions"""
        # Create some questions for this user
        Question.objects.create(
            user=self.user,
            question_text='Question 1',
            answer_text='Answer 1'
        )
        Question.objects.create(
            user=self.user,
            question_text='Question 2',
            answer_text='Answer 2'
        )
        
        # Create question for another user (should not appear in results)
        other_user = User.objects.create_user(username='otheruser', password='pass123')
        Question.objects.create(
            user=other_user,
            question_text='Other user question',
            answer_text='Other user answer'
        )
        
        response = self.client.get('/api/questions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that only this user's questions are returned
        question_texts = [q['question_text'] for q in response.data]
        self.assertIn('Question 1', question_texts)
        self.assertIn('Question 2', question_texts)
        self.assertNotIn('Other user question', question_texts)
    
    def test_list_questions_unauthenticated(self):
        """Test listing questions without authentication"""
        # Remove authentication
        self.client.credentials()
        
        response = self.client.get('/api/questions/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_question_detail(self):
        """Test getting a specific question"""
        question = Question.objects.create(
            user=self.user,
            question_text='Test question',
            answer_text='Test answer'
        )
        
        response = self.client.get(f'/api/questions/{question.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_text'], 'Test question')
        self.assertEqual(response.data['answer_text'], 'Test answer')
    
    def test_get_question_detail_other_user(self):
        """Test getting another user's question (should be forbidden)"""
        other_user = User.objects.create_user(username='otheruser', password='pass123')
        question = Question.objects.create(
            user=other_user,
            question_text='Other user question',
            answer_text='Other user answer'
        )
        
        response = self.client.get(f'/api/questions/{question.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_question_response_fields(self):
        """Test that question response contains expected fields"""
        data = {
            'question': 'Test question for field validation'
        }
        
        response = self.client.post('/api/questions/', data, format='json')
        
        expected_fields = [
            'id', 'user', 'question_text', 'answer_text', 
            'related_article_ids', 'processing_time', 'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, response.data)
        
        # Check that answer is a placeholder for now
        self.assertIn('placeholder', response.data['answer_text'].lower())
        
        # Check that processing_time is recorded
        self.assertIsInstance(response.data['processing_time'], float)
        self.assertGreater(response.data['processing_time'], 0)
