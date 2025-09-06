import json
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import requests
from google import genai
from google.genai import types
from .services import OpenSearchService


@csrf_exempt
@require_http_methods(["POST"])
def ask_question(request):
    """
    Public endpoint for RAG-based question answering
    POST /api/questions/
    Body: {"question": "What are the regulations about the Argentine flag?"}
    """
    start_time = time.time()
    
    try:
        # Parse JSON body
        try:
            body = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Extract question from request
        question_text = body.get('question')
        if not question_text or not question_text.strip():
            return JsonResponse({
                'error': 'Question text is required'
            }, status=400)
        
        # Initialize services
        opensearch_service = OpenSearchService()
        
        # Step 1: Get embedding for the question
        try:
            embedding_response = requests.post(
                f"{settings.EMBEDDING_SERVICE_URL}/embed",
                json={'text': question_text},
                timeout=30
            )
            
            if embedding_response.status_code != 200:
                return JsonResponse({
                    'error': 'Failed to generate embedding for question',
                    'details': embedding_response.text
                }, status=500)
            
            query_embedding = embedding_response.json()['embedding']
            
        except Exception as e:
            return JsonResponse({
                'error': 'Embedding service unavailable',
                'details': str(e)
            }, status=503)
        
        # Step 2: Perform vector search in OpenSearch
        try:
            print(f"DEBUG: About to search for: {question_text}")
            search_results = opensearch_service.search_documents_by_embedding(question_text, size=5)
            print(f"DEBUG: Search results returned: {len(search_results) if search_results else 0}")
            
            if not search_results:
                print(f"DEBUG: No results found for query: {question_text}")
                return JsonResponse({
                    'answer': 'No relevant documents found in the legal database.',
                    'question': question_text,
                    'sources': [],
                    'processing_time': time.time() - start_time
                })
            
        except Exception as e:
            return JsonResponse({
                'error': 'Vector search failed',
                'details': str(e)
            }, status=500)
        
        # Step 3: Build context from search results
        context_parts = []
        sources = []
        
        for result in search_results[:3]:  # Use top 3 results
            norma = result['norma']
            
            # Add document info
            doc_info = f"""
Documento {norma.get('infoleg_id')}: {norma.get('titulo_sumario', '')}
Tipo: {norma.get('tipo_norma', '')} - {norma.get('clase_norma', '')}
Fecha: {norma.get('sancion', '')}
Estado: {norma.get('estado', '')}
"""
            
            # Add relevant content (prefer structured over purified)
            if norma.get('structured_texto_norma'):
                structured = norma['structured_texto_norma']
                if structured.get('preamble'):
                    doc_info += f"\\nPreámbulo: {structured['preamble'][:300]}..."
                if structured.get('articles'):
                    doc_info += "\\nArtículos principales:\\n"
                    for i, article in enumerate(structured['articles'][:3]):  # First 3 articles
                        doc_info += f"Art. {article.get('number', i+1)}: {article.get('body', '')[:200]}...\\n"
            elif norma.get('purified_texto_norma_actualizado'):
                doc_info += f"\\nContenido: {norma['purified_texto_norma_actualizado'][:500]}..."
            elif norma.get('purified_texto_norma'):
                doc_info += f"\\nContenido: {norma['purified_texto_norma'][:500]}..."
            
            context_parts.append(doc_info)
            sources.append({
                'id': norma.get('infoleg_id'),
                'title': norma.get('titulo_sumario', ''),
                'type': f"{norma.get('tipo_norma', '')} - {norma.get('clase_norma', '')}".strip(' -'),
                'date': norma.get('sancion'),
                'score': result['score']
            })
        
        context = "\\n\\n".join(context_parts)
        
        # Step 4: Generate response using Gemini
        try:
            # Initialize Gemini client
            if not settings.GEMINI_API_KEY:
                return JsonResponse({
                    'error': 'Gemini API key not configured'
                }, status=500)
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Create prompt for Gemini
            prompt = f"""Eres un asistente legal especializado en normativa argentina. 

Pregunta del usuario: {question_text}

Información relevante de la base de datos legal:
{context}

Instrucciones:
1. Responde la pregunta basándote ÚNICAMENTE en la información proporcionada
2. Sé preciso y cita los documentos específicos cuando sea relevante
3. Si la información no es suficiente para responder completamente, menciona qué información adicional sería necesaria
4. Usa un tono profesional pero accesible
5. Estructura tu respuesta de manera clara y organizada

Respuesta:"""

            # Generate response
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # More deterministic for legal content
                    max_output_tokens=1000
                )
            )
            
            answer = response.text.strip()
            
        except Exception as e:
            return JsonResponse({
                'error': 'Failed to generate response',
                'details': str(e),
                'fallback_answer': f"Basado en {len(search_results)} documentos encontrados:\\n\\n{context}",
                'question': question_text,
                'sources': sources
            })
        
        # Step 5: Return complete response
        return JsonResponse({
            'answer': answer,
            'question': question_text,
            'sources': sources,
            'documents_found': len(search_results),
            'processing_time': time.time() - start_time
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)