from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    TokenUsageSerializer
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(access),
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """Login user and return JWT tokens"""
    serializer = UserLoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(access),
            }
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def profile(request):
    """Get or update user profile"""
    user = request.user

    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def token_usage(request):
    """Get current user's token usage information"""
    user = request.user

    data = {
        'tokens_used_total': user.tokens_used_total,
        'tokens_used_this_month': user.tokens_used_this_month,
        'monthly_token_limit': user.monthly_token_limit,
        'tokens_remaining': user.tokens_remaining(),
        'role': user.role,
    }

    serializer = TokenUsageSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def auth_status(request):
    """Check if user is authenticated and return basic info"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'role': request.user.role,
                'can_make_prompts': request.user.can_make_prompts(),
                'tokens_remaining': request.user.tokens_remaining(),
            }
        })
    else:
        return Response({
            'authenticated': False,
            'can_make_prompts': False,
        })