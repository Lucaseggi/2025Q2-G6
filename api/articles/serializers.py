from rest_framework import serializers
from .models import Question


class QuestionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'user', 'question_text', 'answer_text', 'related_article_ids', 'processing_time', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'answer_text', 'related_article_ids', 'processing_time', 'created_at', 'updated_at']