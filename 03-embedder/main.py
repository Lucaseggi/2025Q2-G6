"""Main entry point for the embedding microservice"""

import os
import threading
from datetime import datetime

from embedders import create_embedder
from document_processor import DocumentProcessor
from api import app, initialize_embedder


def start_queue_processor(embedder):
    """Start the document processor in a separate thread"""
    processor = DocumentProcessor(embedder)
    processor_thread = threading.Thread(
        target=processor.process_documents_from_queue,
        name="DocumentProcessor",
        daemon=True
    )
    processor_thread.start()
    return processor_thread


def main():
    """Main function to start both queue processor and API server"""
    print("Starting Embedding MS with both queue processor and API server...")

    # Initialize embedder for queue processing
    embedder_type = os.getenv('EMBEDDER_TYPE', 'gemini')
    embedder_config = {
        'model_name': os.getenv('EMBEDDING_MODEL', 'gemini-embedding-001'),
        'output_dimensionality': int(os.getenv('EMBEDDING_DIMENSION', '768')),
        'api_key': os.getenv('GEMINI_API_KEY')
    }

    try:
        embedder = create_embedder(embedder_type, embedder_config)
        if not embedder.is_available():
            print(f"[{datetime.now()}] Main: Embedder not available. Exiting.")
            return

        print(f"[{datetime.now()}] Main: Embedder initialized successfully ({embedder_type})")
        print(f"[{datetime.now()}] Main: Model: {embedder.get_model_name()}")
        print(f"[{datetime.now()}] Main: Dimensions: {embedder.get_embedding_dimension()}")

    except Exception as e:
        print(f"[{datetime.now()}] Main: Error initializing embedder: {e}")
        return

    # Initialize API embedder
    if not initialize_embedder():
        print(f"[{datetime.now()}] Main: Failed to initialize API embedder")
        return

    # Start queue processor in background
    processor_thread = start_queue_processor(embedder)
    print(f"[{datetime.now()}] Main: Document processor thread started")

    # Start API server in a separate thread
    api_thread = threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=int(os.getenv('EMBEDDING_PORT', 8005)),
            debug=os.getenv('DEBUG') == '1'
        ),
        name="APIServer",
        daemon=True
    )
    api_thread.start()
    print(f"[{datetime.now()}] Main: API server thread started on port {os.getenv('EMBEDDING_PORT', 8005)}")

    try:
        # Keep main thread alive and monitor child threads
        while True:
            processor_thread.join(timeout=1.0)
            api_thread.join(timeout=1.0)

            # Check if threads are still alive and restart if needed
            if not processor_thread.is_alive():
                print(f"[{datetime.now()}] Main: Document processor thread died, restarting...")
                processor_thread = start_queue_processor(embedder)

            if not api_thread.is_alive():
                print(f"[{datetime.now()}] Main: API server thread died, restarting...")
                api_thread = threading.Thread(
                    target=lambda: app.run(
                        host='0.0.0.0',
                        port=int(os.getenv('EMBEDDING_PORT', 8005)),
                        debug=os.getenv('DEBUG') == '1'
                    ),
                    name="APIServer",
                    daemon=True
                )
                api_thread.start()

    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Main: Shutting down embedding service...")
        # Cleanup embedder
        try:
            embedder.unload_model()
        except:
            pass


if __name__ == "__main__":
    main()