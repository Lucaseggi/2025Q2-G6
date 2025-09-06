from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'articles'

    def ready(self):
        """Called when Django starts up"""
        # Startup logic removed - documents are now managed via the processing pipeline
        pass
