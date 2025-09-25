"""Data ingestion API endpoints"""

import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny  # Internal service calls
from rest_framework.response import Response
from rest_framework import status

from .services import DataIngestionService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # Internal microservice call
def ingest_norma(request):
    """
    Endpoint for inserter microservice to send processed norma data.

    POST /api/data/ingest/

    Expected data format from inserter:
    {
        "source": "embedding",
        "data": {
            "norma": { ... },           # Complete norma data with LLM metadata
            "embedding": [...],         # Traditional embedding (optional)
            "embedding_model": "...",
            "embedding_source": "...",
            "embedding_type": "...",
            "embedded_at": "...",
        },
        "insert_timestamp": "..."
    }

    This endpoint handles:
    1. Data validation
    2. PostgreSQL insertion (structured data)
    3. OpenSearch insertion (embeddings)
    4. Transaction consistency
    """

    try:
        # Validate request data
        if not request.data:
            return Response({
                'success': False,
                'error': 'No data provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Extract data payload
        data_payload = request.data.get('data')
        if not data_payload:
            return Response({
                'success': False,
                'error': 'Missing data payload'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate norma data
        norma_data = data_payload.get('norma')
        if not norma_data or not norma_data.get('infoleg_id'):
            return Response({
                'success': False,
                'error': 'Missing or invalid norma data'
            }, status=status.HTTP_400_BAD_REQUEST)

        infoleg_id = norma_data['infoleg_id']
        logger.info(f"Received ingestion request for infoleg_id: {infoleg_id}")

        # Process the ingestion
        ingestion_service = DataIngestionService()
        result = ingestion_service.ingest_norma_data(data_payload)

        if result['success']:
            logger.info(f"Successfully ingested data for infoleg_id: {infoleg_id}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            logger.error(f"Ingestion failed for infoleg_id: {infoleg_id}: {result.get('error')}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Ingestion endpoint error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([AllowAny])  # Internal microservice call
def delete_norma(request, infoleg_id):
    """
    Delete norma data from both databases.

    DELETE /api/data/norma/{infoleg_id}/
    """

    try:
        ingestion_service = DataIngestionService()
        result = ingestion_service.delete_norma_data(int(infoleg_id))

        if result['success']:
            logger.info(f"Successfully deleted data for infoleg_id: {infoleg_id}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            logger.error(f"Deletion failed for infoleg_id: {infoleg_id}: {result.get('error')}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid infoleg_id format'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Deletion endpoint error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Internal status check
def ingestion_status(request):
    """
    Health check for data ingestion service.

    GET /api/data/status/
    """

    try:
        # Test database connections
        from django.db import connection
        from chatbot.models import NormaStructured

        # Test PostgreSQL
        postgres_status = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                norma_count = NormaStructured.objects.count()
        except Exception as e:
            postgres_status = f"error: {e}"
            norma_count = 0

        # Test OpenSearch
        opensearch_status = "healthy"
        try:
            ingestion_service = DataIngestionService()
            ingestion_service.opensearch_service.ensure_index_exists()
        except Exception as e:
            opensearch_status = f"error: {e}"

        return Response({
            'service': 'data-ingestion',
            'status': 'healthy' if postgres_status == 'healthy' and opensearch_status == 'healthy' else 'degraded',
            'databases': {
                'postgresql': {
                    'status': postgres_status,
                    'normas_count': norma_count
                },
                'opensearch': {
                    'status': opensearch_status,
                    'index': 'documents'
                }
            }
        })

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return Response({
            'service': 'data-ingestion',
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Debug endpoint
def debug_opensearch_documents(request):
    """
    Debug endpoint to list all documents in OpenSearch with metadata.

    GET /api/data/debug/opensearch/

    Query parameters:
    - limit: Number of documents to return (default: 10, max: 100)
    - infoleg_id: Filter by specific infoleg_id
    - content_type: Filter by content type (document, division, article)
    """

    try:
        ingestion_service = DataIngestionService()
        opensearch_client = ingestion_service.opensearch_service.client
        index_name = ingestion_service.opensearch_service.index_name

        # Parse query parameters
        limit = min(int(request.GET.get('limit', 10)), 100)
        infoleg_id = request.GET.get('infoleg_id')
        content_type = request.GET.get('content_type')

        # Build query
        query = {"match_all": {}}
        filters = []

        if infoleg_id:
            filters.append({"term": {"postgres_pk": int(infoleg_id)}})

        if content_type:
            filters.append({"term": {"content_type": content_type}})

        if filters:
            query = {
                "bool": {
                    "must": [query],
                    "filter": filters
                }
            }

        # Search documents
        search_body = {
            "query": query,
            "size": limit,
            "_source": {
                "excludes": ["embedding"]  # Exclude actual embedding vector
            },
            "sort": [{"postgres_pk": {"order": "asc"}}]
        }

        response = opensearch_client.search(index=index_name, body=search_body)

        documents = []
        for hit in response['hits']['hits']:
            doc = {
                'document_id': hit['_id'],
                'postgres_pk': hit['_source']['postgres_pk'],
                'content_type': hit['_source']['content_type'],
                'embedding_dimensions': 768,  # We know this from our schema
                'metadata': {
                    'sancion': hit['_source'].get('sancion'),
                    'jurisdiccion': hit['_source'].get('jurisdiccion'),
                    'tipo_norma': hit['_source'].get('tipo_norma'),
                    'nro_boletin': hit['_source'].get('nro_boletin'),
                }
            }

            # Add lookup indices if present
            if hit['_source'].get('division_index') is not None:
                doc['division_index'] = hit['_source']['division_index']
            if hit['_source'].get('article_index') is not None:
                doc['article_index'] = hit['_source']['article_index']

            documents.append(doc)

        return Response({
            'total_documents': response['hits']['total']['value'],
            'returned_count': len(documents),
            'documents': documents,
            'query_params': {
                'limit': limit,
                'infoleg_id': infoleg_id,
                'content_type': content_type
            }
        })

    except Exception as e:
        logger.error(f"Debug OpenSearch documents error: {e}")
        return Response({
            'error': 'Failed to query OpenSearch',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Debug endpoint
def debug_opensearch_stats(request):
    """
    Debug endpoint to get OpenSearch index statistics.

    GET /api/data/debug/opensearch/stats/
    """

    try:
        ingestion_service = DataIngestionService()
        opensearch_client = ingestion_service.opensearch_service.client
        index_name = ingestion_service.opensearch_service.index_name

        # Get index stats
        stats_response = opensearch_client.indices.stats(index=index_name)

        # Get aggregations by content type
        agg_response = opensearch_client.search(
            index=index_name,
            body={
                "size": 0,
                "aggs": {
                    "content_types": {
                        "terms": {"field": "content_type"}
                    },
                    "jurisdictions": {
                        "terms": {"field": "jurisdiccion", "size": 20}
                    },
                    "document_types": {
                        "terms": {"field": "tipo_norma", "size": 20}
                    }
                }
            }
        )

        index_stats = stats_response['indices'][index_name]

        return Response({
            'index_name': index_name,
            'total_documents': index_stats['total']['docs']['count'],
            'index_size_bytes': index_stats['total']['store']['size_in_bytes'],
            'content_type_breakdown': {
                bucket['key']: bucket['doc_count']
                for bucket in agg_response['aggregations']['content_types']['buckets']
            },
            'top_jurisdictions': [
                {'jurisdiction': bucket['key'], 'count': bucket['doc_count']}
                for bucket in agg_response['aggregations']['jurisdictions']['buckets'][:10]
            ],
            'top_document_types': [
                {'type': bucket['key'], 'count': bucket['doc_count']}
                for bucket in agg_response['aggregations']['document_types']['buckets'][:10]
            ],
            'schema_info': {
                'embedding_dimensions': 768,
                'vector_method': 'hnsw',
                'space_type': 'cosinesimil'
            }
        })

    except Exception as e:
        logger.error(f"Debug OpenSearch stats error: {e}")
        return Response({
            'error': 'Failed to get OpenSearch stats',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # Debug endpoint
def debug_opensearch_document(request, document_id):
    """
    Debug endpoint to get a specific document with its embedding.

    GET /api/data/debug/opensearch/document/{document_id}/
    """

    try:
        ingestion_service = DataIngestionService()
        document = ingestion_service.opensearch_service.get_document_by_id(document_id)

        if not document:
            return Response({
                'error': f'Document {document_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # For safety, truncate the embedding vector in the response
        # but show the first few dimensions for debugging
        embedding = document.get('embedding', [])
        embedding_preview = embedding[:5] if len(embedding) > 5 else embedding

        response_data = {
            'document_id': document['document_id'],
            'postgres_pk': document['postgres_pk'],
            'content_type': document['content_type'],
            'embedding_info': {
                'total_dimensions': document['embedding_length'],
                'preview_dimensions': embedding_preview,
                'sample_values_range': {
                    'min': min(embedding) if embedding else None,
                    'max': max(embedding) if embedding else None,
                    'avg': sum(embedding) / len(embedding) if embedding else None
                }
            },
            'metadata': {
                'sancion': document.get('sancion'),
                'jurisdiccion': document.get('jurisdiccion'),
                'tipo_norma': document.get('tipo_norma'),
                'nro_boletin': document.get('nro_boletin'),
            }
        }

        # Add lookup indices if present
        if document.get('division_index') is not None:
            response_data['division_index'] = document['division_index']
        if document.get('article_index') is not None:
            response_data['article_index'] = document['article_index']

        return Response(response_data)

    except Exception as e:
        logger.error(f"Debug OpenSearch document error: {e}")
        return Response({
            'error': 'Failed to get document',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)