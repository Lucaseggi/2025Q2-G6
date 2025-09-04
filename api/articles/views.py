from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import requests
import json
import time
from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        start_time = time.time()
        
        question_text = request.data.get('question')
        if not question_text:
            return Response({'error': 'Question text is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create question record
            question = Question.objects.create(
                user=request.user,
                question_text=question_text
            )
            
            # RAG logic would go here:
            # 1. Generate embedding for the question using EC2 embedder
            # 2. Search vector database for similar article embeddings
            # 3. Call LLM with context from retrieved articles
            # 4. Return answer
            
            # Placeholder for now
            answer = "This is a placeholder answer. RAG implementation pending."
            question.answer_text = answer
            question.processing_time = time.time() - start_time
            question.save()
            
            serializer = self.get_serializer(question)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
