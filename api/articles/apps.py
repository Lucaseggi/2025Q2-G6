from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'articles'

    def ready(self):
        """Called when Django starts up - initialize embeddings"""
        # Only run this in the main process, not in management commands or migrations
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            self.initialize_embeddings()

    def initialize_embeddings(self):
        """Initialize embeddings on startup"""
        try:
            from .services import EmbeddingService
            
            logger.info("Starting embedding initialization...")
            embedding_service = EmbeddingService()
            
            # Check if embeddings exist, if not create them
            if not embedding_service.embeddings_exist():
                logger.info("No embeddings found, starting creation process...")
                embedding_service.create_all_embeddings_async()
            else:
                logger.info("Embeddings already exist, skipping creation")
                
        except Exception as e:
            logger.error(f"Error during embedding initialization: {e}")
            # Don't crash the app if embedding setup fails
            pass
