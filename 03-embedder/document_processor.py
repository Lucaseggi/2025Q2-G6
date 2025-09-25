"""Document processing with recursive embedding functionality"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient

from embedders import BaseEmbedder


class DocumentProcessor:
    """Processes documents from the queue and adds recursive embeddings"""

    def __init__(self, embedder: BaseEmbedder):
        self.embedder = embedder
        self.queue_client = RabbitMQClient()

    def add_embeddings_recursively(self, divisions: List[Dict]) -> List[Dict]:
        """
        Recursively add embeddings to divisions and articles.

        For divisions: embedding = title + body
        For articles: embedding = body
        """
        if not divisions:
            return divisions

        processed_divisions = []

        for division in divisions:
            # Create a copy to avoid modifying the original
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
                division_embedding = self.embedder.generate_embedding(division_text.strip())
                if division_embedding:
                    processed_division['embedding'] = division_embedding
                    print(f"[{datetime.now()}] DocumentProcessor: Generated embedding for division '{processed_division.get('name', 'unnamed')}'")

            # Process articles in this division
            if division.get('articles'):
                processed_articles = []
                for article in division['articles']:
                    processed_article = self.add_embeddings_to_article(article)
                    processed_articles.append(processed_article)
                processed_division['articles'] = processed_articles

            # Recursively process nested divisions
            if division.get('divisions'):
                processed_division['divisions'] = self.add_embeddings_recursively(division['divisions'])

            processed_divisions.append(processed_division)

        return processed_divisions

    def add_embeddings_to_article(self, article: Dict) -> Dict:
        """
        Add embeddings to an article and its nested articles recursively.

        For articles: embedding = body
        """
        processed_article = article.copy()

        # Generate embedding for article body
        if article.get('body') and article['body'].strip():
            article_embedding = self.embedder.generate_embedding(article['body'].strip())
            if article_embedding:
                processed_article['embedding'] = article_embedding
                print(f"[{datetime.now()}] DocumentProcessor: Generated embedding for article '{processed_article.get('ordinal', 'no ordinal')}'")

        # Recursively process nested articles
        if article.get('articles'):
            processed_nested_articles = []
            for nested_article in article['articles']:
                processed_nested_article = self.add_embeddings_to_article(nested_article)
                processed_nested_articles.append(processed_nested_article)
            processed_article['articles'] = processed_nested_articles

        return processed_article

    def process_single_document(self, message_body: Dict) -> Optional[Dict]:
        """Process a single document and return embedded data"""
        try:
            # The message body is now a ProcessedData object with 'norma' and 'processing_timestamp'
            norma = message_body.get('norma', {})
            norma_id = norma.get('infoleg_id', 'unknown')

            print(f"[{datetime.now()}] DocumentProcessor: Processing document {norma_id}")

            # Check if we have structured data from LLM processing
            structured_data = None
            content_source = None

            # Prioritize structured data from texto_norma_actualizado
            if norma.get('structured_texto_norma_actualizado'):
                structured_data = norma['structured_texto_norma_actualizado']
                content_source = "structured_texto_norma_actualizado"
            elif norma.get('structured_texto_norma'):
                structured_data = norma['structured_texto_norma']
                content_source = "structured_texto_norma"

            if structured_data and structured_data.get('divisions'):
                print(
                    f"[{datetime.now()}] DocumentProcessor: Processing structured data for document {norma_id} from {content_source}"
                )
                print(f"Found {len(structured_data['divisions'])} divisions to process")

                # Process structured data recursively to add embeddings
                processed_divisions = self.add_embeddings_recursively(structured_data['divisions'])

                # Update the structured data with embeddings
                updated_structured_data = structured_data.copy()
                updated_structured_data['divisions'] = processed_divisions

                # Update the norma with the embedded structured data
                if content_source == "structured_texto_norma_actualizado":
                    norma['structured_texto_norma_actualizado'] = updated_structured_data
                else:
                    norma['structured_texto_norma'] = updated_structured_data

                # Create embedded data with structured content
                embedded_data = {
                    'norma': norma,
                    'embedding_model': self.embedder.get_model_name(),
                    'embedding_source': content_source,
                    'embedded_at': datetime.now().isoformat(),
                    'embedding_type': 'structured_recursive'
                }

            else:
                # Fallback to traditional embedding if no structured data available
                print(
                    f"[{datetime.now()}] DocumentProcessor: No structured data found for document {norma_id}, falling back to traditional embedding"
                )

                # Determine which text to embed - prefer purified_texto_actualizado over purified_texto_norma
                content_to_embed = None

                if norma.get('purified_texto_norma_actualizado'):
                    content_to_embed = norma['purified_texto_norma_actualizado']
                    content_source = "purified_texto_norma_actualizado"
                elif norma.get('purified_texto_norma'):
                    content_to_embed = norma['purified_texto_norma']
                    content_source = "purified_texto_norma"
                else:
                    # Fallback to texto_resumido which is always present
                    if norma.get('texto_resumido') and norma['texto_resumido'].strip():
                        content_to_embed = norma['texto_resumido']
                        content_source = "texto_resumido"
                    else:
                        # Final fallback to basic norm info
                        basic_info = f"{norma.get('titulo_sumario', '')} {norma.get('titulo_resumido', '')}".strip()
                        if basic_info:
                            content_to_embed = basic_info
                            content_source = "basic_info"

                if not content_to_embed:
                    print(
                        f"[{datetime.now()}] DocumentProcessor: No content found for document {norma_id}"
                    )
                    # Still send to inserting queue even with no content
                    embedded_data = {
                        'norma': norma,
                        'embedding_model': self.embedder.get_model_name(),
                        'embedding_source': 'no_content',
                        'embedded_at': datetime.now().isoformat(),
                        'embedding_type': 'none'
                    }
                else:
                    print(
                        f"[{datetime.now()}] DocumentProcessor: Using content from {content_source} for document {norma_id}"
                    )
                    print(f"Content length: {len(content_to_embed)} characters")

                    # Generate embedding
                    embedding_vector = self.embedder.generate_embedding(content_to_embed)

                    if embedding_vector is None:
                        print(
                            f"[{datetime.now()}] DocumentProcessor: Failed to generate embedding for document {norma_id}"
                        )
                        # Still send to inserting queue even with failed embedding
                        embedded_data = {
                            'norma': norma,
                            'embedding_model': self.embedder.get_model_name(),
                            'embedding_source': content_source,
                            'embedded_at': datetime.now().isoformat(),
                            'embedding_type': 'failed'
                        }
                    else:
                        print(
                            f"[{datetime.now()}] DocumentProcessor: Generated {len(embedding_vector)}-dimensional embedding"
                        )

                        # Create embedded data with traditional embedding
                        embedded_data = {
                            'norma': norma,
                            'embedding': embedding_vector,
                            'embedding_model': self.embedder.get_model_name(),
                            'embedding_source': content_source,
                            'embedded_at': datetime.now().isoformat(),
                            'embedding_type': 'traditional'
                        }

            return embedded_data

        except Exception as e:
            print(f"[{datetime.now()}] DocumentProcessor: Error processing document: {e}")
            return None

    def process_documents_from_queue(self):
        """Main processing loop - listen for documents and process them"""
        print("DocumentProcessor started - listening for messages...")

        while True:
            try:
                # Receive message from embedding queue
                message_body = self.queue_client.receive_message('embedding', timeout=20)

                if message_body:
                    print(f"[{datetime.now()}] DocumentProcessor: Received message")

                    # DEBUG: Print the complete dequeued message for analysis
                    print("=" * 100)
                    print("COMPLETE DEQUEUED MESSAGE FROM PROCESSING-MS:")
                    print("=" * 100)
                    print(json.dumps(message_body, indent=2, default=str))
                    print("=" * 100)

                    # Process the document
                    embedded_data = self.process_single_document(message_body)

                    if embedded_data:
                        # Send to inserting queue
                        insert_message = {
                            "source": "embedding",
                            "data": embedded_data,
                            "insert_timestamp": datetime.now().isoformat(),
                        }

                        success = self.queue_client.send_message('inserting', insert_message)

                        if success:
                            norma_id = embedded_data.get('norma', {}).get('infoleg_id', 'unknown')
                            print(
                                f"[{datetime.now()}] DocumentProcessor: Successfully processed and sent document {norma_id} to inserting queue"
                            )
                        else:
                            print(f"[{datetime.now()}] DocumentProcessor: Failed to send message to inserting queue")

            except Exception as e:
                print(f"[{datetime.now()}] DocumentProcessor: Error in processing loop: {e}")
                # Wait before retrying
                time.sleep(5)