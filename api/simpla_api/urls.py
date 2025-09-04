from django.contrib import admin
from django.urls import path, include
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy', 'message': 'Simpla API is running'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('auth_api.urls')),
    path('api/', include('articles.urls')),
    path('health/', health_check, name='health_check'),
]