import requests
import json
import logging
import threading
import os
from pathlib import Path
from django.conf import settings
from opensearchpy import OpenSearch

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service for managing OpenSearch operations with the new document structure"""
    
    def __init__(self):
        self.opensearch_endpoint = settings.OPENSEARCH_ENDPOINT
        self.embedding_service_url = settings.EMBEDDING_SERVICE_URL
        self.client = OpenSearch(
            hosts=[self.opensearch_endpoint],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
        self.index_name = "documents"
    
    def search_documents(self, query_text, size=10):
        """Search documents using text search on relevant fields"""
        try:
            search_body = {
                "size": size,
                "query": {
                    "multi_match": {
                        "query": query_text,
                        "fields": [
                            "norma.titulo_sumario^3",
                            "norma.titulo_resumido^3", 
                            "norma.purified_texto_norma^2",
                            "norma.purified_texto_norma_actualizado^2",
                            "norma.observaciones",
                            "norma.structured_texto_norma",
                            "norma.structured_texto_norma_actualizado"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "highlight": {
                    "fields": {
                        "norma.titulo_sumario": {},
                        "norma.purified_texto_norma": {"fragment_size": 150, "number_of_fragments": 3}
                    }
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                result = {
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'norma': doc['norma'],
                    'highlight': hit.get('highlight', {}),
                    'embedded_at': doc.get('embedded_at')
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching OpenSearch: {e}")
            return []
    
    def get_document_by_id(self, doc_id):
        """Get a specific document by its ID"""
        try:
            response = self.client.get(
                index=self.index_name,
                id=doc_id
            )
            return response['_source']
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def get_documents_count(self):
        """Get total number of documents in the index"""
        try:
            response = self.client.count(index=self.index_name)
            return response['count']
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0
    
    def search_documents_by_embedding(self, query_text, size=10):
        """Search documents using vector similarity"""
        try:
            # Get embedding for the query text
            embedding_response = requests.post(
                f"{self.embedding_service_url}/embed",
                json={'text': query_text},
                timeout=30
            )
            
            if embedding_response.status_code != 200:
                logger.error(f"Failed to get embedding: {embedding_response.text}")
                return []
            
            query_embedding = embedding_response.json()['embedding']
            print(f"DEBUG: Query text: {query_text}")
            print(f"DEBUG: Query embedding length: {len(query_embedding)}")
            
            # Use script_score query as alternative to KNN for vector similarity
            search_body = {
                "size": size,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                            "params": {"query_vector": query_embedding}
                        }
                    }
                },
                "_source": {
                    "excludes": ["embedding"]  # Don't return the large embedding vector
                }
            }
            
            print(f"DEBUG: Search body: {json.dumps(search_body, indent=2)[:500]}...")
            
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            print(f"DEBUG: Search response: {json.dumps(response, indent=2)[:1000]}...")
            
            results = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                result = {
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'norma': doc['norma'],
                    'embedding_source': doc.get('embedding_source'),
                    'embedded_at': doc.get('embedded_at')
                }
                results.append(result)
            
            print(f"DEBUG: Results count: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            print(f"DEBUG: Vector search exception: {e}")
            return []


class EmbeddingService:
    """Legacy service for managing embeddings with EC2 embedder and vector database"""
    
    def __init__(self):
        self.ec2_embedder_url = settings.EC2_EMBEDDER_URL
        self.vector_db_url = settings.VECTOR_DB_URL
        
    def embeddings_exist(self):
        """Check if embeddings already exist in vector database"""
        try:
            response = requests.get(f"{self.vector_db_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('total_embeddings', 0) > 0
        except Exception as e:
            logger.warning(f"Could not check embedding status: {e}")
            
        return False
    
    def create_all_embeddings_async(self):
        """Start embedding creation in background thread"""
        thread = threading.Thread(target=self._create_all_embeddings)
        thread.daemon = True
        thread.start()
        logger.info("Embedding creation started in background thread")
    
    def _create_all_embeddings(self):
        """Create embeddings for all articles (runs in background)"""
        try:
            articles = self._load_articles_from_json()
            total_articles = len(articles)
            
            logger.info(f"Starting to create embeddings for {total_articles} articles")
            
            created_count = 0
            batch_size = 100  # Process in batches
            
            for i in range(0, total_articles, batch_size):
                batch = articles[i:i + batch_size]
                batch_success = self._process_batch(batch, i // batch_size + 1)
                created_count += batch_success
                
                logger.info(f"Processed batch {i//batch_size + 1}, created {batch_success} embeddings")
                
            logger.info(f"Embedding creation completed. Created {created_count}/{total_articles} embeddings")
            
        except Exception as e:
            logger.error(f"Error during bulk embedding creation: {e}")
    
    def _process_batch(self, articles, batch_num):
        """Process a batch of articles"""
        created_count = 0
        
        for article in articles:
            try:
                if self._create_embedding_for_article(article):
                    created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create embedding for article {article.get('unique_id')}: {e}")
                
        return created_count
    
    def _create_embedding_for_article(self, article):
        """Create embedding for a single article"""
        try:
            # Step 1: Generate embedding using EC2 embedder
            embedding_data = {
                'text': article['text'],
                'metadata': {
                    'article_id': article['unique_id'],
                    'article_number': article['article_number'],
                    'province': article['province'],
                    'date': article['date'],
                    'source': article['source']
                }
            }
            
            response = requests.post(
                f"{self.ec2_embedder_url}/embed",
                json=embedding_data,
                timeout=30
            )
            
            if response.status_code != 200:
                return False
                
            embedding_result = response.json()
            
            # Step 2: Store embedding in vector database
            vector_data = {
                'id': article['unique_id'],
                'embedding': embedding_result['embedding'],
                'metadata': embedding_data['metadata']
            }
            
            vector_response = requests.post(
                f"{self.vector_db_url}/store",
                json=vector_data,
                timeout=10
            )
            
            return vector_response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Error creating embedding for {article.get('unique_id')}: {e}")
            return False
    
    def search_similar_articles(self, question_text, top_k=5):
        """Search for similar articles using vector similarity"""
        try:
            # Generate embedding for the question
            response = requests.post(
                f"{self.ec2_embedder_url}/embed",
                json={'text': question_text},
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            question_embedding = response.json()['embedding']
            
            # Search vector database
            search_response = requests.post(
                f"{self.vector_db_url}/search",
                json={
                    'embedding': question_embedding,
                    'top_k': top_k
                },
                timeout=10
            )
            
            if search_response.status_code == 200:
                return search_response.json().get('results', [])
                
        except Exception as e:
            logger.error(f"Error searching similar articles: {e}")
            
        return []
    
    def _load_articles_from_json(self):
        """Load all articles from JSON files"""
        articles = []
        articles_directory = Path('article_parsing_constituciones')
        
        if not articles_directory.exists():
            return articles
        
        json_files = list(articles_directory.glob('*.json'))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    file_articles = json.load(f)
                    
                for article in file_articles:
                    # Add a unique identifier combining file info and article number
                    article['unique_id'] = f"{json_file.stem}_{article['article_number']}"
                    articles.append(article)
                    
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(f"Error reading {json_file}: {e}")
                continue
        
        return articles