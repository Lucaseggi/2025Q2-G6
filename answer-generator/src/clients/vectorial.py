"""Client for communicating with the vectorial microservice via REST API."""

import os
import requests
from typing import List, Dict, Any, Optional


def search_vectors(
    embedding: List[float],
    filters: Optional[Dict[str, str]] = None,
    limit: int = 10,
    api_base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for similar vectors in the vectorial microservice via REST API.

    Args:
        embedding: The embedding vector to search with
        filters: Optional metadata filters
        limit: Maximum number of results to return (default: 10)
        api_base_url: The API base URL (default: from VECTORIAL_API_HOST env var)

    Returns:
        dict with keys: success (bool), message (str), results (list)
    """
    if api_base_url is None:
        api_base_url = os.getenv("VECTORIAL_API_HOST", "http://localhost:8080")

    base_url = api_base_url.rstrip('/')
    url = f"{base_url}/api/v1/vectorial/search"

    # Build the request payload
    payload = {
        "embedding": embedding,
        "filters": filters if filters else {},
        "limit": limit
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Convert results to dict format
        results = []
        for result in data.get("results", []):
            results.append({
                "document_id": result.get("documentId"),
                "score": result.get("score"),
                "metadata": result.get("metadata", {})
            })

        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "results": results
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"HTTP error: {str(e)}",
            "results": []
        }
