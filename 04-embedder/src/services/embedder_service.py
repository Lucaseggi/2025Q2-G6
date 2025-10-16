"""Main embedding service implementation"""

import time
from datetime import datetime
from typing import Optional, Dict, List, Any

# Add src to path for interfaces
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.embedder_service_interface import EmbedderServiceInterface
from interfaces.norm_embedder_service_interface import NormEmbedderServiceInterface

# Add shared models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData, EmbedderMetadata
from structured_logger import StructuredLogger, LogStage

logger = StructuredLogger("embedder", "service")


class EmbedderService(EmbedderServiceInterface):
    """Main embedder service that coordinates document processing"""

    def __init__(self, norm_embedder_service: NormEmbedderServiceInterface):
        """
        Initialize embedding service with dependency injection.

        Args:
            norm_embedder_service: The norm embedder service implementation
        """
        self.norm_embedder_service = norm_embedder_service

    def process_document(self, input_data: ProcessedData) -> Optional[ProcessedData]:
        """Process a document and add embeddings to its structured data"""
        start_time = time.time()

        try:
            infoleg_response = input_data.scraping_data.infoleg_response
            norma_id = infoleg_response.infoleg_id

            logger.info(
                "Starting embedding generation",
                stage=LogStage.EMBEDDING,
                infoleg_id=norma_id
            )

            # Check if we have processing data
            if not input_data.processing_data:
                logger.warning(
                    "No processing data found",
                    infoleg_id=norma_id
                )
                return input_data

            # Look for structured data in parsings
            parsings = input_data.processing_data.parsings
            structured_data = None
            content_source = None

            # Prioritize updated_text over original_text
            if "updated_text" in parsings and parsings["updated_text"].structured_data:
                structured_data = parsings["updated_text"].structured_data
                content_source = "updated_text"
            elif "original_text" in parsings and parsings["original_text"].structured_data:
                structured_data = parsings["original_text"].structured_data
                content_source = "original_text"

            if structured_data and structured_data.get('divisions'):
                logger.info(
                    f"Processing structured data from {content_source}",
                    stage=LogStage.EMBEDDING,
                    infoleg_id=norma_id,
                    content_source=content_source,
                    num_divisions=len(structured_data['divisions'])
                )

                # Process structured data recursively to add embeddings
                processed_divisions = self._add_embeddings_recursively(structured_data['divisions'])

                # Update the structured data with embeddings
                updated_structured_data = structured_data.copy()
                updated_structured_data['divisions'] = processed_divisions

                # Update the parsing with embedded structured data
                parsings[content_source].structured_data = updated_structured_data

            else:
                # Fallback to traditional embedding if no structured data available
                logger.info(
                    "No structured data found, using traditional embedding",
                    stage=LogStage.EMBEDDING,
                    infoleg_id=norma_id
                )
                self._add_traditional_embedding(input_data)

            # Generate embedding for summarized_text if available
            self._add_summarized_text_embedding(input_data, norma_id)

            # Create embedder metadata
            embedder_metadata = EmbedderMetadata(
                embedding_model_used=self.norm_embedder_service.get_model_name(),
                embedding_tokens_used=100,  # Placeholder
                embedding_timestamp=datetime.now().isoformat()
            )

            # Add embedder metadata to processing data
            input_data.processing_data.embedder_metadata = embedder_metadata

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Embedding generation complete",
                stage=LogStage.EMBEDDING,
                infoleg_id=norma_id,
                duration_ms=duration_ms,
                model=self.norm_embedder_service.get_model_name()
            )

            return input_data

        except Exception as e:
            logger.error(
                f"Error generating embeddings: {str(e)}",
                stage=LogStage.EMBEDDING,
                infoleg_id=norma_id if 'norma_id' in locals() else None,
                error_type=type(e).__name__
            )
            return None

    def _add_embeddings_recursively(self, divisions: List[Dict]) -> List[Dict]:
        """Recursively add embeddings to divisions and articles"""
        if not divisions:
            return divisions

        processed_divisions = []

        for division in divisions:
            processed_division = division.copy()

            # Generate embedding for division (title + body)
            division_text = ""
            if division.get('title'):
                division_text += division['title']
            if division.get('body'):
                if division_text:
                    division_text += " " + division['body']
                else:
                    division_text = division['body']

            if division_text.strip():
                division_embedding = self.norm_embedder_service.generate_embedding(division_text.strip())
                if division_embedding:
                    processed_division['embedding'] = division_embedding

            # Process articles in this division
            if division.get('articles'):
                processed_articles = []
                for article in division['articles']:
                    processed_article = self._add_embeddings_to_article(article)
                    processed_articles.append(processed_article)
                processed_division['articles'] = processed_articles

            # Recursively process nested divisions
            if division.get('divisions'):
                processed_division['divisions'] = self._add_embeddings_recursively(division['divisions'])

            processed_divisions.append(processed_division)

        return processed_divisions

    def _add_embeddings_to_article(self, article: Dict) -> Dict:
        """Add embeddings to an article and its nested articles recursively"""
        processed_article = article.copy()

        # Generate embedding for article body
        if article.get('body') and article['body'].strip():
            article_embedding = self.norm_embedder_service.generate_embedding(article['body'].strip())
            if article_embedding:
                processed_article['embedding'] = article_embedding

        # Recursively process nested articles
        if article.get('articles'):
            processed_nested_articles = []
            for nested_article in article['articles']:
                processed_nested_article = self._add_embeddings_to_article(nested_article)
                processed_nested_articles.append(processed_nested_article)
            processed_article['articles'] = processed_nested_articles

        return processed_article

    def _add_traditional_embedding(self, input_data: ProcessedData):
        """Add traditional embedding if no structured data available"""
        # Determine which text to embed from purifications
        purifications = input_data.processing_data.purifications
        content_to_embed = None
        content_source = None

        # Prefer updated_text over original_text
        if purifications.get("updated_text") and purifications["updated_text"].strip():
            content_to_embed = purifications["updated_text"]
            content_source = "updated_text"
        elif purifications.get("original_text") and purifications["original_text"].strip():
            content_to_embed = purifications["original_text"]
            content_source = "original_text"

        if content_to_embed:
            embedding_vector = self.norm_embedder_service.generate_embedding(content_to_embed)
            if embedding_vector and content_source in input_data.processing_data.parsings:
                input_data.processing_data.parsings[content_source].embeddings = embedding_vector

    def _add_summarized_text_embedding(self, input_data: ProcessedData, norma_id: int):
        """Generate and add embedding for summarized text (summarized_text)"""
        purifications = input_data.processing_data.purifications

        summarized_text = purifications.get("summarized_text")

        if summarized_text and summarized_text.strip():
            logger.info(
                "Generating embedding for summarized text",
                stage=LogStage.EMBEDDING,
                infoleg_id=norma_id
            )

            summarized_text_embedding = self.norm_embedder_service.generate_embedding(summarized_text.strip())

            if summarized_text_embedding:
                input_data.processing_data.summarized_text_embedding = summarized_text_embedding
                logger.info(
                    "Summarized text embedding generated successfully",
                    stage=LogStage.EMBEDDING,
                    infoleg_id=norma_id,
                    embedding_dimension=len(summarized_text_embedding)
                )
            else:
                logger.warning(
                    "Failed to generate summarized text embedding",
                    stage=LogStage.EMBEDDING,
                    infoleg_id=norma_id
                )

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text prompt"""
        try:
            return self.norm_embedder_service.generate_embedding(text)
        except Exception as e:
            self.logger.error(f"Error generating embedding for text: {e}")
            return None

    def is_available(self) -> bool:
        """Check if the embedding service is available"""
        return self.norm_embedder_service.is_available()