from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/status/', views.auth_status, name='auth_status'),

    # User management
    path('profile/', views.profile, name='profile'),
    path('token-usage/', views.token_usage, name='token_usage'),
]