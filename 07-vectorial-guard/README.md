# Vectorial Guard Service

A gRPC-based guard service that provides a unified interface for multiple vector database backends. This service abstracts vector storage operations, allowing you to switch between different vector database providers without changing your application code.

## Supported Vector Databases

The service currently supports:
- **OpenSearch** (default)
- **Pinecone**

## Configuration

The vector database backend is selected via the `VECTOR_STORE_TYPE` environment variable. If not specified, it defaults to OpenSearch.

### OpenSearch Configuration

To use OpenSearch as your vector database:

```bash
# Vector store selection
VECTOR_STORE_TYPE=opensearch

# OpenSearch connection settings
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_SCHEME=http
OPENSEARCH_INDEX=documents

# Optional: Authentication (for production)
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin123
```

### Pinecone Configuration

To use Pinecone as your vector database:

```bash
# Vector store selection
VECTOR_STORE_TYPE=pinecone

# Pinecone connection settings
PINECONE_API_KEY=your-api-key-here
PINECONE_INDEX_NAME=documents
PINECONE_ENVIRONMENT=gcp-starter
```

**Important:** The `PINECONE_API_KEY` is required when using Pinecone. You can obtain an API key from your [Pinecone console](https://app.pinecone.io/).

## Architecture

The service uses a factory pattern to instantiate the appropriate vector store implementation:

```
VectorStoreFactory
    ├── OpenSearchVectorStore (implements VectorStoreService)
    └── PineconeVectorStore (implements VectorStoreService)
```

All implementations conform to the `VectorStoreService` interface, which provides:
- `initialize()` - Initialize the connection
- `getDocumentCount()` - Get total document count
- `isHealthy()` - Health check
- `storeDocument()` - Store a document with embeddings
- `searchDocuments()` - Search for similar documents
- `shutdown()` - Clean up resources

## Building

Build the service using Maven:

```bash
mvn clean package
```

This will generate protobuf classes and create a fat JAR with all dependencies.

## Running

### Local Development

```bash
java -jar target/vectorial-guard-1.0.0-jar-with-dependencies.jar
```

### Docker

Build and run using Docker:

```bash
docker build -t vectorial-guard .
docker run -p 50052:50052 \
  -e VECTOR_STORE_TYPE=pinecone \
  -e PINECONE_API_KEY=your-key \
  -e PINECONE_INDEX_NAME=documents \
  vectorial-guard
```

## gRPC Interface

The service exposes a gRPC interface on port 50052 with the following methods:
- `GetStatus` - Get service status and configuration
- `StoreDocument` - Store a document with embeddings
- `SearchDocuments` - Search for similar documents

## Adding New Vector Stores

To add a new vector database backend:

1. Create a new implementation class in `com.simpla.vectorial.service.impl` that implements `VectorStoreService`
2. Add the dependency to `pom.xml`
3. Update `VectorStoreFactory.java` to include the new type
4. Document the configuration in this README

## Dependencies

Key dependencies:
- **gRPC** (1.58.0) - Service communication
- **OpenSearch Java Client** (2.10.0) - OpenSearch vector store
- **Pinecone Client** (4.0.1) - Pinecone vector store
- **Jackson** (2.15.2) - JSON processing

## Performance Considerations

### OpenSearch
- Uses HNSW algorithm for approximate nearest neighbor search
- Configurable via index settings (ef_search, ef_construction, m)
- Suitable for self-hosted deployments

### Pinecone
- Fully managed service
- Automatic scaling and optimization
- Best for cloud-native applications
- Requires API key and active subscription
