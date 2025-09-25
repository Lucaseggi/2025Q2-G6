from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    return JsonResponse({'status': 'healthy', 'message': 'Simpla Legal RAG API is running'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/chatbot/', include('chatbot.urls')),
    path('api/data/', include('data_ingestion.urls')),
    path('health/', health_check, name='health_check'),
]