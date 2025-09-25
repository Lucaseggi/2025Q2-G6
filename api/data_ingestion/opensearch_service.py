"""OpenSearch service for vector operations"""

import logging
from typing import Dict, List, Optional, Any
from opensearchpy import OpenSearch
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service to handle OpenSearch operations for vector embeddings"""

    def __init__(self):
        self.client = self._create_client()
        self.index_name = "documents"

    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client"""
        try:
            client = OpenSearch(
                hosts=[settings.OPENSEARCH_ENDPOINT],
                http_compress=True,
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            return client
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {e}")
            raise

    def ensure_index_exists(self) -> bool:
        """Create index if it doesn't exist"""
        try:
            if not self.client.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            # Vector and identification
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": 768,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "nmslib"
                                }
                            },
                            "postgres_pk": {"type": "integer"},  # Reference to PostgreSQL
                            "content_type": {"type": "keyword"},  # document, division, article

                            # Lookup indexes (for structured content)
                            "division_index": {"type": "integer"},
                            "article_index": {"type": "integer"},

                            # Essential filtering fields only
                            "sancion": {"type": "date"},
                            "jurisdiccion": {"type": "keyword"},
                            "tipo_norma": {"type": "keyword"},
                            "nro_boletin": {"type": "keyword"}
                        }
                    }
                }

                self.client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created OpenSearch index '{self.index_name}'")

            return True
        except Exception as e:
            logger.error(f"Failed to ensure index exists: {e}")
            return False

    def insert_document_with_embeddings(self, norma_data: Dict[str, Any]) -> bool:
        """
        Insert document with embeddings to OpenSearch.

        For structured data with recursive embeddings, creates multiple documents:
        - Main document with traditional embedding (if exists)
        - Division documents with their embeddings
        - Article documents with their embeddings
        """
        try:
            norma = norma_data['norma']
            infoleg_id = norma['infoleg_id']

            # Ensure index exists
            if not self.ensure_index_exists():
                return False

            documents_to_insert = []

            # Check if we have a traditional embedding (fallback)
            if norma_data.get('embedding'):
                main_doc = {
                    # Vector and identification
                    'embedding': norma_data['embedding'],
                    'postgres_pk': infoleg_id,  # Reference to PostgreSQL
                    'content_type': 'document',

                    # Essential filtering fields only
                    'sancion': norma.get('sancion'),  # Date filtering
                    'jurisdiccion': norma.get('jurisdiccion'),  # Jurisdiction filtering
                    'tipo_norma': norma.get('tipo_norma'),  # Type filtering
                    'nro_boletin': norma.get('nro_boletin'),  # Bulletin filtering
                }
                documents_to_insert.append((f"doc_{infoleg_id}", main_doc))

            # Process structured data with recursive embeddings
            structured_data = norma.get('structured_texto_norma_actualizado') or norma.get('structured_texto_norma')

            if structured_data and structured_data.get('divisions'):
                # Extract all divisions and articles with embeddings
                self._extract_embedded_content(
                    structured_data['divisions'],
                    infoleg_id,
                    norma,
                    documents_to_insert
                )

            # Bulk insert all documents
            if documents_to_insert:
                bulk_body = []
                for doc_id, doc_data in documents_to_insert:
                    bulk_body.append({"index": {"_index": self.index_name, "_id": doc_id}})
                    bulk_body.append(doc_data)

                response = self.client.bulk(body=bulk_body)

                if response.get('errors'):
                    logger.error(f"Bulk insert errors for infoleg_id {infoleg_id}: {response}")
                    return False

                logger.info(f"Inserted {len(documents_to_insert)} documents for infoleg_id {infoleg_id}")
                return True
            else:
                logger.warning(f"No embeddings found for infoleg_id {infoleg_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to insert document {norma_data.get('norma', {}).get('infoleg_id')}: {e}")
            return False

    def _extract_embedded_content(self, divisions: List[Dict], infoleg_id: int, norma: Dict, documents_to_insert: List):
        """Recursively extract divisions and articles with embeddings"""

        for div_idx, division in enumerate(divisions):
            # Insert division if it has an embedding
            if division.get('embedding'):
                div_doc = {
                    # Vector and identification
                    'embedding': division['embedding'],
                    'postgres_pk': infoleg_id,  # Reference to parent norma
                    'content_type': 'division',
                    'division_index': div_idx,  # For PostgreSQL lookup

                    # Essential filtering fields only
                    'sancion': norma.get('sancion'),
                    'jurisdiccion': norma.get('jurisdiccion'),
                    'tipo_norma': norma.get('tipo_norma'),
                    'nro_boletin': norma.get('nro_boletin'),
                }
                documents_to_insert.append((f"div_{infoleg_id}_{div_idx}", div_doc))

            # Process articles in this division
            if division.get('articles'):
                for art_idx, article in enumerate(division['articles']):
                    if article.get('embedding'):
                        art_doc = {
                            # Vector and identification
                            'embedding': article['embedding'],
                            'postgres_pk': infoleg_id,  # Reference to parent norma
                            'content_type': 'article',
                            'division_index': div_idx,  # For PostgreSQL lookup
                            'article_index': art_idx,   # For PostgreSQL lookup

                            # Essential filtering fields only
                            'sancion': norma.get('sancion'),
                            'jurisdiccion': norma.get('jurisdiccion'),
                            'tipo_norma': norma.get('tipo_norma'),
                            'nro_boletin': norma.get('nro_boletin'),
                        }
                        documents_to_insert.append((f"art_{infoleg_id}_{div_idx}_{art_idx}", art_doc))

            # Process nested divisions recursively
            if division.get('divisions'):
                self._extract_embedded_content(division['divisions'], infoleg_id, norma, documents_to_insert)

    def delete_document(self, infoleg_id: int) -> bool:
        """Delete all documents related to a norma by infoleg_id"""
        try:
            # Delete by query to remove all documents with this postgres_pk
            delete_query = {
                "query": {
                    "term": {
                        "postgres_pk": infoleg_id
                    }
                }
            }

            response = self.client.delete_by_query(
                index=self.index_name,
                body=delete_query
            )

            deleted_count = response.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} documents for infoleg_id {infoleg_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete documents for infoleg_id {infoleg_id}: {e}")
            return False

    def search_similar_documents(self, query_embedding: List[float], size: int = 10) -> List[Dict]:
        """Search for similar documents using vector similarity"""
        try:
            search_body = {
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": size
                        }
                    }
                },
                "size": size
            }

            response = self.client.search(index=self.index_name, body=search_body)

            results = []
            for hit in response['hits']['hits']:
                result = {
                    'postgres_pk': hit['_source']['postgres_pk'],
                    'score': hit['_score'],
                    'content_type': hit['_source'].get('content_type', 'document'),
                    'division_index': hit['_source'].get('division_index'),
                    'article_index': hit['_source'].get('article_index'),
                    # Include filter fields for immediate use
                    'sancion': hit['_source'].get('sancion'),
                    'jurisdiccion': hit['_source'].get('jurisdiccion'),
                    'tipo_norma': hit['_source'].get('tipo_norma'),
                    'nro_boletin': hit['_source'].get('nro_boletin'),
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """Get a specific document by its ID, including the embedding vector"""
        try:
            response = self.client.get(index=self.index_name, id=document_id)

            if response['found']:
                doc = response['_source']
                doc['document_id'] = response['_id']
                doc['embedding_length'] = len(doc.get('embedding', []))
                return doc
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None