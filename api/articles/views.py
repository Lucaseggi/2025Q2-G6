from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import requests
import json
import time
from .models import Question
from .serializers import QuestionSerializer
from .services import OpenSearchService


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
            
            # Search OpenSearch for relevant documents
            opensearch_service = OpenSearchService()
            search_results = opensearch_service.search_documents(question_text, size=5)
            
            if search_results:
                # Format context from search results
                context_parts = []
                for result in search_results:
                    norma = result['norma']
                    context_parts.append(f"""
Documento {norma.get('infoleg_id')}: {norma.get('titulo_sumario', '')}
Tipo: {norma.get('tipo_norma', '')} - {norma.get('clase_norma', '')}
Estado: {norma.get('estado', '')}
""")
                    
                    # Add relevant text content
                    if norma.get('purified_texto_norma_actualizado'):
                        context_parts.append(f"Contenido actualizado: {norma['purified_texto_norma_actualizado'][:500]}...")
                    elif norma.get('purified_texto_norma'):
                        context_parts.append(f"Contenido: {norma['purified_texto_norma'][:500]}...")
                
                context = "\n\n".join(context_parts)
                answer = f"Basado en {len(search_results)} documentos encontrados:\n\n{context}\n\n[Implementar LLM aquí para generar respuesta más sofisticada]"
            else:
                answer = "No se encontraron documentos relevantes para tu consulta."
            
            question.answer_text = answer
            question.processing_time = time.time() - start_time
            question.save()
            
            serializer = self.get_serializer(question)
            response_data = serializer.data
            response_data['search_results_count'] = len(search_results) if search_results else 0
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
