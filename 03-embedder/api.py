"""API endpoints for the embedding service"""

import os
from datetime import datetime
from flask import Flask, request, jsonify

from embedders import create_embedder

app = Flask(__name__)

# Global embedder instance
embedder = None


def initialize_embedder():
    """Initialize the embedder based on configuration"""
    global embedder

    embedder_type = os.getenv('EMBEDDER_TYPE', 'gemini')
    embedder_config = {
        'model_name': os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001'),
        'output_dimensionality': int(os.getenv('EMBEDDING_DIMENSION', '768')),
        'api_key': os.getenv('GEMINI_API_KEY')
    }

    try:
        embedder = create_embedder(embedder_type, embedder_config)
        if embedder.is_available():
            print(f"[{datetime.now()}] API: Embedder initialized successfully ({embedder_type})")
            return True
        else:
            print(f"[{datetime.now()}] API: Embedder not available ({embedder_type})")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] API: Error initializing embedder: {e}")
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    global embedder

    embedder_status = "unknown"
    if embedder:
        embedder_status = "available" if embedder.is_available() else "unavailable"

    return jsonify({
        'status': 'healthy',
        'service': 'embedding-ms',
        'embedder_status': embedder_status,
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/embedder/info', methods=['GET'])
def embedder_info():
    """Get information about the current embedder"""
    global embedder

    if not embedder:
        return jsonify({'error': 'Embedder not initialized'}), 500

    try:
        info = embedder.get_model_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/embed', methods=['POST'])
def embed_text():
    """Generate embedding for user prompt"""
    global embedder

    if not embedder:
        return jsonify({'error': 'Embedder not initialized'}), 500

    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Text field is required'}), 400

        text = data['text']
        if not text.strip():
            return jsonify({'error': 'Text cannot be empty'}), 400

        print(
            f"[{datetime.now()}] API: Generating embedding for user text ({len(text)} chars)"
        )

        # Generate embedding
        embedding = embedder.generate_embedding(text)

        if embedding is None:
            return jsonify({'error': 'Failed to generate embedding'}), 500

        response = {
            'embedding': embedding,
            'model': embedder.get_model_name(),
            'dimensions': len(embedding),
            'embedder_type': embedder.get_embedder_type().value,
            'timestamp': datetime.now().isoformat(),
        }

        return jsonify(response)

    except Exception as e:
        print(f"[{datetime.now()}] API: Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/embed/batch', methods=['POST'])
def embed_batch():
    """Generate embeddings for multiple texts"""
    global embedder

    if not embedder:
        return jsonify({'error': 'Embedder not initialized'}), 500

    try:
        data = request.get_json()

        if not data or 'texts' not in data:
            return jsonify({'error': 'Texts field is required'}), 400

        texts = data['texts']
        if not isinstance(texts, list):
            return jsonify({'error': 'Texts must be a list'}), 400

        if not texts:
            return jsonify({'error': 'Texts list cannot be empty'}), 400

        # Validate all texts
        for i, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                return jsonify({'error': f'Text at index {i} is invalid'}), 400

        print(
            f"[{datetime.now()}] API: Generating embeddings for {len(texts)} texts"
        )

        # Generate embeddings
        embeddings = embedder.batch_generate_embeddings(texts)

        # Check for failures
        failed_indices = [i for i, emb in enumerate(embeddings) if emb is None]
        if failed_indices:
            print(f"[{datetime.now()}] API: Failed to generate embeddings for indices: {failed_indices}")

        response = {
            'embeddings': embeddings,
            'model': embedder.get_model_name(),
            'dimensions': embedder.get_embedding_dimension(),
            'embedder_type': embedder.get_embedder_type().value,
            'total_texts': len(texts),
            'successful_embeddings': len([emb for emb in embeddings if emb is not None]),
            'failed_indices': failed_indices,
            'timestamp': datetime.now().isoformat(),
        }

        return jsonify(response)

    except Exception as e:
        print(f"[{datetime.now()}] API: Error in batch embedding: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    # Initialize embedder
    if initialize_embedder():
        port = int(os.getenv('EMBEDDING_PORT', 8005))
        debug_mode = os.getenv('DEBUG') == '1'
        print(f"Embedding API server starting on port {port} (debug={debug_mode})")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    else:
        print("Failed to initialize embedder. Exiting.")
        exit(1)