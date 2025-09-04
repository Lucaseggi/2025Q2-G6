# Simpla API

A minimal Django REST API for RAG (Retrieval-Augmented Generation) coordination with JWT authentication.

## Features

- **JWT Authentication** (register, login, profile)
- **Questions API** (ask questions, get RAG answers)
- **Startup Embedding Process** (automatically creates embeddings on startup)
- **EC2 Integration Ready** (embedder and vector database)
- **Constitutional Articles** (5,689 articles from Argentine provinces)

## Quick Start

### 1. Environment Setup

Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Generate Secure Keys

Generate a new Django secret key:
```bash
openssl rand -base64 50
```

Update your `.env` file with the generated key:
```bash
SECRET_KEY=your-generated-key-here
```

### 3. Configure Services

Update your `.env` file with your service URLs:
```bash
EC2_EMBEDDER_URL=http://your-embedder-ec2:8001
VECTOR_DB_URL=http://your-vector-db:8002
GEMINI_API_KEY=your-gemini-api-key
```

### 4. Run with Docker

```bash
# Build and start
docker compose up -d

# Check health
curl http://localhost:8000/health/
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login  
- `GET /api/auth/profile/` - User profile

### Questions
- `POST /api/questions/` - Ask a question
- `GET /api/questions/` - List user's questions

### Health
- `GET /health/` - Health check

## Example Usage

### 1. Register a user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass123","email":"user@example.com"}'
```

### 2. Ask a question
```bash
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"question":"What are the constitutional rights in Argentina?"}'
```

## Testing

Run the test suite:
```bash
docker compose run --rm web python manage.py test
```

## Architecture

### Startup Process
1. Django starts up
2. Checks if embeddings exist in vector database
3. If not found, starts background embedding creation
4. Reads 5,689 articles from JSON files
5. Calls EC2 embedder for each article
6. Stores embeddings in vector database

### EC2 Services Expected

**Embedder Service (port 8001):**
- `POST /embed` - Generate embeddings
  ```json
  {
    "text": "article text",
    "metadata": {...}
  }
  ```

**Vector Database (port 8002):**
- `GET /status` - Check if embeddings exist
- `POST /store` - Store embeddings
- `POST /search` - Similarity search

## Development

### Project Structure
```
├── articles/           # Questions model and RAG logic
├── auth_api/          # JWT authentication
├── article_parsing_constituciones/  # JSON files (5,689 articles)
├── simpla_api/        # Django settings
├── docker-compose.yml # Container setup
└── .env              # Environment variables
```

### Database
- **SQLite** for authentication and questions only
- **Vector Database** (external) for embeddings
- **JSON files** for article content

## Production Notes

1. **Security**: Generate new SECRET_KEY for production
2. **Database**: Consider PostgreSQL for production
3. **Environment**: Set `DEBUG=0` in production
4. **CORS**: Configure `CORS_ALLOWED_ORIGINS` for your frontend
5. **Static Files**: Configure static file serving

## License

This project is for demonstration purposes.