from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'organization', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            **validated_data,
            role='basic'  # Default role
        )
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
        else:
            raise serializers.ValidationError('Must include email and password.')

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information"""
    full_name = serializers.ReadOnlyField()
    tokens_remaining = serializers.ReadOnlyField()
    can_make_prompts = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'organization', 'role', 'tokens_used_total', 'tokens_used_this_month',
            'monthly_token_limit', 'tokens_remaining', 'can_make_prompts',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'role', 'tokens_used_total', 'tokens_used_this_month', 'created_at', 'updated_at']


class TokenUsageSerializer(serializers.Serializer):
    """Serializer for token usage information"""
    tokens_used_total = serializers.IntegerField()
    tokens_used_this_month = serializers.IntegerField()
    monthly_token_limit = serializers.IntegerField(allow_null=True)
    tokens_remaining = serializers.IntegerField(allow_null=True)
    role = serializers.CharField()