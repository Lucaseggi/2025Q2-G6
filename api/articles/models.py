from django.db import models
from django.contrib.auth.models import User


class Question(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    related_article_ids = models.JSONField(default=list, blank=True)  # Store article references as JSON
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
        ]
