from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access and token tracking"""

    USER_ROLES = [
        ('admin', 'Administrator'),
        ('premium', 'Premium User'),
        ('basic', 'Basic User'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='basic')

    # Token usage tracking (for premium/basic users)
    tokens_used_total = models.BigIntegerField(default=0)
    tokens_used_this_month = models.IntegerField(default=0)
    monthly_token_limit = models.IntegerField(null=True, blank=True)  # null = unlimited

    # Reset date for monthly token counting
    tokens_reset_date = models.DateField(auto_now_add=True)

    # Profile
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    organization = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def can_make_prompts(self):
        """Only authenticated users can make prompts (no anonymous)"""
        return self.is_authenticated

    def can_access_admin(self):
        """Only admins can access admin interface"""
        return self.role == 'admin'

    def has_token_limit(self):
        """Check if user has a monthly token limit"""
        return self.monthly_token_limit is not None and self.role != 'admin'

    def tokens_remaining(self):
        """Get remaining tokens for this month"""
        if not self.has_token_limit():
            return None  # Unlimited
        return max(0, self.monthly_token_limit - self.tokens_used_this_month)

    def can_use_tokens(self, token_count):
        """Check if user can use specified number of tokens"""
        if self.role == 'admin':
            return True
        if not self.has_token_limit():
            return True
        return self.tokens_remaining() >= token_count

    def use_tokens(self, token_count):
        """Record token usage"""
        from django.utils import timezone
        from datetime import date

        # Check if we need to reset monthly counter
        today = date.today()
        if today.month != self.tokens_reset_date.month or today.year != self.tokens_reset_date.year:
            self.tokens_used_this_month = 0
            self.tokens_reset_date = today

        # Add tokens
        self.tokens_used_total += token_count
        self.tokens_used_this_month += token_count
        self.save(update_fields=['tokens_used_total', 'tokens_used_this_month', 'tokens_reset_date'])


class PromptHistory(models.Model):
    """Track user prompts and token usage"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prompts')
    prompt_text = models.TextField()
    response_summary = models.TextField(blank=True)  # First 200 chars of response

    # Token tracking
    tokens_used = models.IntegerField()
    model_used = models.CharField(max_length=100)

    # Performance
    response_time_ms = models.IntegerField(null=True, blank=True)
    results_found = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prompt_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: {self.prompt_text[:50]}... ({self.tokens_used} tokens)"