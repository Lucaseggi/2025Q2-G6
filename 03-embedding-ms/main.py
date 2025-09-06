import json
import os
import boto3
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
import numpy as np

# Initialize Gemini client - will be done after environment variables are loaded

app = Flask(__name__)

def create_sqs_client():
    return boto3.client(
        'sqs',
        endpoint_url=os.getenv('SQS_ENDPOINT'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

def get_gemini_client():
    """Initialize Gemini client with API key"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print(f"[{datetime.now()}] Embedding: ERROR - GEMINI_API_KEY environment variable not set")
        return None
    
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        print(f"[{datetime.now()}] Embedding: Error initializing Gemini client: {e}")
        return None

def generate_gemini_embedding(text):
    """Generate embedding using Gemini"""
    try:
        client = get_gemini_client()
        if not client:
            return None
            
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,  # Pass text directly, not as a list
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        
        # Extract the embedding values as a list
        [embedding_obj] = result.embeddings
        embedding = list(embedding_obj.values)
        
        print(f"[{datetime.now()}] Embedding: Generated {len(embedding)}-dimensional embedding")
        return embedding
        
    except Exception as e:
        print(f"[{datetime.now()}] Embedding: Error generating Gemini embedding: {e}")
        return None

def process_document_embedding():
    """Process documents from the queue"""
    print("Embedding MS document processor started - listening for messages...")
    
    sqs = create_sqs_client()
    embedding_queue_url = os.getenv('EMBEDDING_QUEUE_URL')
    inserting_queue_url = os.getenv('INSERTING_QUEUE_URL')
    
    while True:
        try:
            # Poll for messages
            response = sqs.receive_message(
                QueueUrl=embedding_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    print(f"[{datetime.now()}] Embedding: Received message")
                    
                    # Parse message
                    message_body = json.loads(message['Body'])
                    
                    # DEBUG: Print the complete dequeued message for analysis
                    print("="*100)
                    print("COMPLETE DEQUEUED MESSAGE FROM PROCESSING-MS:")
                    print("="*100)
                    print(json.dumps(message_body, indent=2, default=str))
                    print("="*100)
                    
                    # The message body is now a ProcessedData object with 'norma' and 'processing_timestamp'
                    norma = message_body.get('norma', {})
                    
                    # Determine which text to embed - prefer purified_texto_actualizado over purified_texto_norma
                    content_to_embed = None
                    content_source = None
                    
                    if norma.get('purified_texto_norma_actualizado'):
                        content_to_embed = norma['purified_texto_norma_actualizado']
                        content_source = "purified_texto_norma_actualizado"
                    elif norma.get('purified_texto_norma'):
                        content_to_embed = norma['purified_texto_norma']
                        content_source = "purified_texto_norma"
                    else:
                        # Fallback to basic norm info if no purified text
                        basic_info = f"{norma.get('titulo_sumario', '')} {norma.get('titulo_resumido', '')}".strip()
                        if basic_info:
                            content_to_embed = basic_info
                            content_source = "basic_info"
                    
                    if not content_to_embed:
                        print(f"[{datetime.now()}] Embedding: No content found for document {norma.get('infoleg_id')}")
                        # Still need to delete the message to avoid reprocessing
                        sqs.delete_message(
                            QueueUrl=embedding_queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        continue
                    
                    print(f"[{datetime.now()}] Embedding: Using content from {content_source} for document {norma.get('infoleg_id')}")
                    print(f"Content length: {len(content_to_embed)} characters")
                    
                    # Generate embedding using Gemini
                    embedding_vector = generate_gemini_embedding(content_to_embed)
                    
                    if embedding_vector is None:
                        print(f"[{datetime.now()}] Embedding: Failed to generate embedding for document {norma.get('infoleg_id')}")
                        # Still delete the message to avoid infinite retries
                        sqs.delete_message(
                            QueueUrl=embedding_queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        continue
                    
                    print(f"[{datetime.now()}] Embedding: Generated {len(embedding_vector)}-dimensional embedding")
                    
                    # Create embedded data with simplified structure
                    embedded_data = {
                        'norma': norma,
                        'embedding': embedding_vector,
                        'embedding_model': 'gemini-embedding-001',
                        'embedding_source': content_source,
                        'embedded_at': datetime.now().isoformat()
                    }
                    
                    # Send to inserting queue
                    insert_message = {
                        "source": "embedding",
                        "data": embedded_data,
                        "insert_timestamp": datetime.now().isoformat()
                    }
                    
                    sqs.send_message(
                        QueueUrl=inserting_queue_url,
                        MessageBody=json.dumps(insert_message)
                    )
                    
                    # Delete processed message
                    sqs.delete_message(
                        QueueUrl=embedding_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                    print(f"[{datetime.now()}] Embedding: Generated embedding for document {norma.get('infoleg_id')} and sent to inserting queue")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Embedding: Error: {type(e).__name__}: {e}")
            # Try to show the raw message if parsing failed
            try:
                if 'Messages' in response:
                    for msg in response['Messages']:
                        print("RAW MESSAGE BODY:")
                        print(msg['Body'][:1000] + "..." if len(msg['Body']) > 1000 else msg['Body'])
            except:
                pass

# API Endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'embedding-ms',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/embed', methods=['POST'])
def embed_text():
    """Generate embedding for user prompt"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Text field is required'}), 400
        
        text = data['text']
        if not text.strip():
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        print(f"[{datetime.now()}] Embedding API: Generating embedding for user text ({len(text)} chars)")
        
        # Generate embedding
        embedding = generate_gemini_embedding(text)
        
        if embedding is None:
            return jsonify({'error': 'Failed to generate embedding'}), 500
        
        response = {
            'embedding': embedding,
            'model': 'gemini-embedding-001',
            'dimensions': len(embedding),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[{datetime.now()}] Embedding API: Error: {e}")
        return jsonify({'error': str(e)}), 500

def start_queue_processor():
    """Start the queue processor in a separate thread"""
    queue_thread = threading.Thread(target=process_document_embedding, daemon=True)
    queue_thread.start()

def main():
    """Main function to start both queue processor and API server"""
    print("Starting Embedding MS with both queue processor and API server...")
    
    # Debug: Check if API key is available
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"[{datetime.now()}] Gemini API key found (length: {len(api_key)} chars)")
    else:
        print(f"[{datetime.now()}] WARNING: GEMINI_API_KEY environment variable not set!")
    
    # Start queue processor in background
    start_queue_processor()
    
    # Start Flask API server
    port = int(os.getenv('EMBEDDING_API_PORT', 8001))
    print(f"Embedding API server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()