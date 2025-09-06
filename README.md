# Simpla

This project is composed of:
- Data Extraction Pipeline: which includes a scraper, a processor, an embedder, an inserter and a queue coordinating the communication.
- Augmented Retrieval Response: which is handled by the API in coordination with the embedder and the vector database.

Both areas require interaction with the Gemini API, and the extraction requires interaction with the Infoleg API.

## Running

Instance all the services, which include the Data Extraction pipeline and the API that coordinates the augmented retrieval and response
```bash
docker compose up --build
```

More commands can be used through the `Makefile`

## Using the Application

A query can be performed to the vector database in order to get the amount of elements just to verify:

```bash
curl -X GET "http://localhost:9200/documents/_count"
```

Then a query to the API can be made:
```bash
curl -X POST http://localhost:8000/api/questions/   -H "Content-Type: application/json"   -d '{"question": "Cuales son las regulaciones de la bandera argentina?"}'
```
