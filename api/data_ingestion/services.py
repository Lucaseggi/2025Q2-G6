"""Data ingestion services for handling norma data"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from chatbot.models import NormaStructured, Division, Article
from .opensearch_service import OpenSearchService

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Service to handle complete data ingestion workflow"""

    def __init__(self):
        self.opensearch_service = OpenSearchService()

    def ingest_norma_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete data ingestion workflow:
        1. Validate incoming data
        2. Save to PostgreSQL (structured data)
        3. Save to OpenSearch (vector embeddings)
        4. Return status
        """
        try:
            # Extract main components
            norma_data = data.get('norma', {})
            embedding_metadata = {
                'embedding_model': data.get('embedding_model'),
                'embedding_source': data.get('embedding_source'),
                'embedding_type': data.get('embedding_type'),
                'embedded_at': data.get('embedded_at'),
                'inserted_at': data.get('insert_timestamp')
            }

            if not norma_data.get('infoleg_id'):
                raise ValueError("Missing infoleg_id in norma data")

            infoleg_id = norma_data['infoleg_id']

            # Two-phase commit: PostgreSQL first, then OpenSearch
            # If OpenSearch fails, we need to rollback PostgreSQL
            postgres_result = None
            opensearch_result = None

            try:
                # Step 1: Save to PostgreSQL (with transaction)
                with transaction.atomic():
                    postgres_result = self._save_to_postgres(norma_data, embedding_metadata)

                # Step 2: Save to OpenSearch (outside PostgreSQL transaction)
                opensearch_result = self._save_to_opensearch(data)

                # If OpenSearch fails, rollback PostgreSQL
                if not opensearch_result.get('status') == 'success':
                    logger.error(f"OpenSearch failed for {infoleg_id}, rolling back PostgreSQL")

                    # Rollback PostgreSQL changes
                    with transaction.atomic():
                        from chatbot.models import NormaStructured
                        NormaStructured.objects.filter(infoleg_id=infoleg_id).delete()

                    return {
                        'success': False,
                        'error': 'OpenSearch insertion failed, PostgreSQL changes rolled back',
                        'postgres': postgres_result,
                        'opensearch': opensearch_result,
                        'timestamp': timezone.now().isoformat()
                    }

                # Both operations successful
                logger.info(f"Data ingestion completed for infoleg_id {infoleg_id}")
                logger.info(f"PostgreSQL: {postgres_result['status']}")
                logger.info(f"OpenSearch: {opensearch_result['status']}")

                return {
                    'success': True,
                    'infoleg_id': infoleg_id,
                    'postgres': postgres_result,
                    'opensearch': opensearch_result,
                    'timestamp': timezone.now().isoformat()
                }

            except Exception as postgres_error:
                # PostgreSQL failed, no need to rollback OpenSearch
                logger.error(f"PostgreSQL transaction failed for {infoleg_id}: {postgres_error}")
                raise postgres_error

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

    def _save_to_postgres(self, norma_data: Dict, embedding_metadata: Dict) -> Dict[str, Any]:
        """Save structured norma data to PostgreSQL"""
        try:
            infoleg_id = norma_data['infoleg_id']

            # Parse dates
            sancion = None
            publicacion = None
            if norma_data.get('sancion'):
                try:
                    sancion = datetime.fromisoformat(norma_data['sancion']).date()
                except (ValueError, TypeError):
                    pass

            if norma_data.get('publicacion'):
                try:
                    publicacion = datetime.fromisoformat(norma_data['publicacion']).date()
                except (ValueError, TypeError):
                    pass

            # Parse embedded_at timestamp
            embedded_at = None
            if embedding_metadata.get('embedded_at'):
                try:
                    embedded_at = datetime.fromisoformat(embedding_metadata['embedded_at'])
                except (ValueError, TypeError):
                    pass

            # Create or update norma
            norma, created = NormaStructured.objects.update_or_create(
                infoleg_id=infoleg_id,
                defaults={
                    'jurisdiccion': norma_data.get('jurisdiccion'),
                    'clase_norma': norma_data.get('clase_norma'),
                    'tipo_norma': norma_data.get('tipo_norma'),
                    'sancion': sancion,
                    'id_normas': norma_data.get('id_normas'),
                    'publicacion': publicacion,
                    'titulo_sumario': norma_data.get('titulo_sumario'),
                    'titulo_resumido': norma_data.get('titulo_resumido'),
                    'observaciones': norma_data.get('observaciones'),
                    'nro_boletin': norma_data.get('nro_boletin'),
                    'pag_boletin': norma_data.get('pag_boletin'),
                    'texto_resumido': norma_data.get('texto_resumido'),
                    'texto_norma': norma_data.get('texto_norma'),
                    'texto_norma_actualizado': norma_data.get('texto_norma_actualizado'),
                    'estado': norma_data.get('estado'),
                    'lista_normas_que_complementa': norma_data.get('lista_normas_que_complementa'),
                    'lista_normas_que_la_complementan': norma_data.get('lista_normas_que_la_complementan'),

                    # Processed fields
                    'purified_texto_norma': norma_data.get('purified_texto_norma'),
                    'purified_texto_norma_actualizado': norma_data.get('purified_texto_norma_actualizado'),

                    # Embedding metadata
                    'embedding_model': embedding_metadata.get('embedding_model'),
                    'embedding_source': embedding_metadata.get('embedding_source'),
                    'embedded_at': embedded_at,
                    'embedding_type': embedding_metadata.get('embedding_type'),

                    # LLM metadata
                    'llm_model_used': norma_data.get('llm_model_used'),
                    'llm_models_used': norma_data.get('llm_models_used'),
                    'llm_tokens_used': norma_data.get('llm_tokens_used'),
                    'llm_processing_time': norma_data.get('llm_processing_time'),
                    'llm_similarity_score': norma_data.get('llm_similarity_score'),
                }
            )

            # Process structured data (divisions and articles)
            divisions_created = 0
            articles_created = 0

            # Clear existing divisions/articles if updating
            if not created:
                norma.divisions.all().delete()

            # Get structured data
            structured_data = (norma_data.get('structured_texto_norma_actualizado') or
                             norma_data.get('structured_texto_norma'))

            if structured_data and structured_data.get('divisions'):
                division_results = self._create_divisions_recursive(
                    norma, structured_data['divisions'], None
                )
                divisions_created = division_results['divisions_created']
                articles_created = division_results['articles_created']

            return {
                'status': 'created' if created else 'updated',
                'norma_id': norma.id,
                'divisions_created': divisions_created,
                'articles_created': articles_created
            }

        except Exception as e:
            logger.error(f"PostgreSQL save failed: {e}")
            raise

    def _create_divisions_recursive(self, norma: NormaStructured, divisions: List[Dict],
                                   parent_division: Optional[Division] = None) -> Dict[str, int]:
        """Recursively create divisions and articles"""
        divisions_created = 0
        articles_created = 0

        for division_data in divisions:
            # Create division
            division = Division.objects.create(
                norma=norma,
                parent_division=parent_division,
                name=division_data.get('name'),
                ordinal=division_data.get('ordinal'),
                title=division_data.get('title'),
                body=division_data.get('body'),
                order_index=division_data.get('order')
            )
            divisions_created += 1

            # Create articles in this division
            if division_data.get('articles'):
                article_results = self._create_articles_recursive(
                    division, division_data['articles'], None
                )
                articles_created += article_results

            # Create nested divisions
            if division_data.get('divisions'):
                nested_results = self._create_divisions_recursive(
                    norma, division_data['divisions'], division
                )
                divisions_created += nested_results['divisions_created']
                articles_created += nested_results['articles_created']

        return {
            'divisions_created': divisions_created,
            'articles_created': articles_created
        }

    def _create_articles_recursive(self, division: Division, articles: List[Dict],
                                  parent_article: Optional[Article] = None) -> int:
        """Recursively create articles"""
        articles_created = 0

        for article_data in articles:
            article = Article.objects.create(
                division=division,
                parent_article=parent_article,
                ordinal=article_data.get('ordinal'),
                body=article_data.get('body', ''),
                order_index=article_data.get('order')
            )
            articles_created += 1

            # Create nested articles
            if article_data.get('articles'):
                nested_count = self._create_articles_recursive(
                    division, article_data['articles'], article
                )
                articles_created += nested_count

        return articles_created

    def _save_to_opensearch(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save embeddings to OpenSearch"""
        try:
            success = self.opensearch_service.insert_document_with_embeddings(data)

            if success:
                return {
                    'status': 'success',
                    'index': 'documents'
                }
            else:
                return {
                    'status': 'failed',
                    'error': 'OpenSearch insertion failed'
                }

        except Exception as e:
            logger.error(f"OpenSearch save failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def delete_norma_data(self, infoleg_id: int) -> Dict[str, Any]:
        """Delete norma data from both databases"""
        try:
            with transaction.atomic():
                # Delete from PostgreSQL
                postgres_deleted = NormaStructured.objects.filter(infoleg_id=infoleg_id).delete()

                # Delete from OpenSearch
                opensearch_success = self.opensearch_service.delete_document(infoleg_id)

                return {
                    'success': True,
                    'infoleg_id': infoleg_id,
                    'postgres_deleted': postgres_deleted[0],
                    'opensearch_success': opensearch_success,
                    'timestamp': timezone.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Data deletion failed for infoleg_id {infoleg_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }