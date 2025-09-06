# Simpla Legal RAG API

A stateless Django REST API for legal document question-answering using RAG (Retrieval-Augmented Generation) with Argentine legal documents.

## Features

- **Stateless RAG API** - No database or authentication required
- **Vector Search** - Semantic search using Gemini embeddings in OpenSearch
- **Legal Document Processing** - LLM-structured legal content from InfoLEG
- **Professional Legal Assistant** - Specialized responses for Argentine legal queries
- **Source Attribution** - Returns specific document references and scores

## Architecture

The complete system consists of:
1. **Scraper MS** - Extracts legal documents from InfoLEG API
2. **Processing MS** - Purifies HTML and structures content using Gemini LLM
3. **Embedding MS** - Generates semantic embeddings using Gemini
4. **Inserter MS** - Stores documents and vectors in OpenSearch
5. **Django API** - RAG endpoint for question answering

## Quick Start

### 1. Environment Setup

Make sure you have the Gemini API key in your `.env` file:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

### 2. Run with Docker Compose

```bash
# Start the complete pipeline
docker compose up -d

# Check API health
curl http://localhost:8000/health/
```

### 3. Test the RAG Endpoint

```bash
# Ask a question about Argentine legal documents
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Cuales son las regulaciones de la bandera argentina?"}'
```

## API Endpoint

### Questions (RAG)
- `POST /api/questions/` - Ask legal questions (public, no auth required)

**Request:**
```json
{
  "question": "What are the regulations about the Argentine flag?"
}
```

**Response:**
```json
{
  "answer": "Based on Document 183532 (SIMBOLOS PATRIOS), a decree from May 19, 1869, the Argentine flag regulations include:\n\n**Article 1**: The Argentine flag shall be raised on all public buildings and may be raised on private houses during patriotic commemorations. This right extends to foreigners who wish to participate.\n\n**Article 2**: It is prohibited to display flags of other states on land, except at diplomatic agents' and consuls' residences.\n\n**Article 3**: In facade decorations and halls prepared for public festivities, all flags may be used, but the Argentine flag must occupy the center or the highest positions.\n\nThis decree was signed by President Sarmiento and ensures proper respect for national symbols during patriotic celebrations.",
  "question": "What are the regulations about the Argentine flag?",
  "sources": [
    {
      "id": 183532,
      "title": "SIMBOLOS PATRIOS",
      "type": "Decreto",
      "date": "1869-05-19",
      "score": 0.87
    }
  ],
  "documents_found": 1,
  "processing_time": 2.5
}
```

### Health Check
- `GET /health/` - API health status

## RAG Pipeline Flow

1. **Question Reception** → Validates user input
2. **Embedding Generation** → Calls embedding-ms to vectorize question
3. **Vector Search** → Searches OpenSearch for similar legal documents
4. **Context Building** → Extracts relevant content from top matches
5. **LLM Response** → Uses Gemini to generate professional legal answer
6. **Response Formatting** → Returns structured JSON with sources

## Test Examples

### Basic Flag Regulation Query
```bash
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuáles son las regulaciones sobre la bandera argentina?"}'
```

### Legal Rights Query  
```bash
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the legal requirements for diplomatic flags in Argentina?"}'
```

### Constitutional Query
```bash
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué dice la normativa argentina sobre símbolos patrios?"}'
```

## Error Handling

The API provides detailed error responses:

```json
{
  "error": "Embedding service unavailable",
  "details": "Connection timeout to embedding-ms"
}
```

Common error scenarios:
- **400**: Invalid or missing question text
- **500**: Embedding service unavailable
- **500**: Vector search failed
- **503**: OpenSearch unavailable

## Dependencies

- **Django 4.2.0** - Web framework
- **djangorestframework** - REST API
- **opensearch-py** - Vector database client
- **google-genai** - LLM integration
- **requests** - HTTP client

## Development

### Project Structure
```
api/
├── articles/           # RAG logic and OpenSearch integration
├── simpla_api/         # Django settings (stateless config)
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container definition
└── README.md          # This file
```

### Key Components
- **OpenSearchService** - Vector search and document retrieval
- **ask_question view** - Complete RAG pipeline implementation
- **Stateless config** - No database, auth, or sessions

### Adding New Features
1. All logic is in `articles/views.py`
2. OpenSearch operations in `articles/services.py`  
3. No models needed (stateless)
4. Test with curl commands above

## Production Notes

1. **Security**: Configure CORS for your frontend domain
2. **Environment**: Set `DEBUG=0` in production
3. **Scaling**: API is stateless and scales horizontally
4. **Monitoring**: Add logging and metrics as needed
5. **Rate Limiting**: Consider adding rate limiting for public endpoint

## Legal Document Coverage

Currently indexed:
- **Argentine Flag Regulations** (Decree 183532, 1869)
- **National Symbols** legislation
- Additional documents processed by the scraper pipeline

The system can be extended to include more legal documents by running the scraper with different parameters.

## License

This project is for demonstration and educational purposes.