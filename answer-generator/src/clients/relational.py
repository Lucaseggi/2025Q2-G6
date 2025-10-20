"""Client for communicating with the relational microservice via REST API."""

import os
import requests
from typing import List, Dict, Any, Optional


def fetch_norm_by_infoleg_id(
    infoleg_id: int,
    api_base_url: Optional[str] = None
) -> dict:
    """
    Fetch norm data from the relational microservice via REST API.

    Args:
        infoleg_id: The infoleg ID to fetch
        api_base_url: The API base URL (default: from RELATIONAL_API_HOST env var)

    Returns:
        dict with keys: success (bool), message (str), norma_json (str)
    """
    if api_base_url is None:
        api_base_url = os.getenv("RELATIONAL_API_HOST", "http://localhost:8090")

    base_url = api_base_url.rstrip('/')
    url = f"{base_url}/api/v1/relational/reconstruct"
    params = {"infoleg_id": infoleg_id}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        norma_json = data.get("normaJson", "")  # API returns camelCase

        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "norma_json": norma_json
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"API error: {str(e)}",
            "norma_json": ""
        }


def fetch_norm_by_id(
    norm_id: int,
    api_base_url: Optional[str] = None
) -> dict:
    """
    Fetch norm data from the relational microservice via REST API by database ID.

    Args:
        norm_id: The database ID to fetch
        api_base_url: The API base URL (default: from RELATIONAL_API_HOST env var)

    Returns:
        dict with keys: success (bool), message (str), norma_json (str)
    """
    if api_base_url is None:
        api_base_url = os.getenv("RELATIONAL_API_HOST", "http://localhost:8090")

    base_url = api_base_url.rstrip('/')
    url = f"{base_url}/api/v1/relational/reconstruct/{norm_id}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        norma_json = data.get("normaJson", "")  # API returns camelCase

        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "norma_json": norma_json
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"API error: {str(e)}",
            "norma_json": ""
        }


def fetch_batch_entities(
    search_results: List[Dict],
    api_base_url: Optional[str] = None
) -> dict:
    """
    Fetch batch entities (articles and divisions) from the relational microservice via REST API.

    Args:
        search_results: List of search result dicts with 'document_id' and 'metadata' fields
                       document_id format: "n{source_id}_{type_prefix}{id}" (e.g., "n183532_a4", "n183532_d1")
                       metadata must contain 'document_type' field ("article" or "division")
        api_base_url: The API base URL (default: from RELATIONAL_API_HOST env var)

    Returns:
        dict with keys: success (bool), message (str), normas_json (str)
    """
    if api_base_url is None:
        api_base_url = os.getenv("RELATIONAL_API_HOST", "http://localhost:8090")

    entity_pairs = _parse_entity_pairs_from_search_results(search_results)
    base_url = api_base_url.rstrip('/')
    url = f"{base_url}/api/v1/relational/batch"

    payload = {
        "entities": entity_pairs
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "normas_json": data.get("normasJson", "[]")  # API returns camelCase
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"API error: {str(e)}",
            "normas_json": "[]"
        }


def _parse_entity_pairs_from_search_results(search_results: List[Dict]) -> List[Dict[str, Any]]:
    """
    Parse search results and create entity pair dicts for API request.

    Args:
        search_results: List of search result dicts

    Returns:
        List of entity pair dicts with 'type' and 'id' keys
    """
    entity_pairs = []
    for result in search_results:
        metadata = result.get("metadata", {})
        document_type = metadata.get("document_type", "")
        document_id = metadata.get("document_id", "")

        # Convert document_id from string to int
        try:
            document_id_int = int(document_id)
        except (ValueError, TypeError):
            continue

        entity_pair = {
            "type": document_type,
            "id": document_id_int
        }
        entity_pairs.append(entity_pair)

    return entity_pairs
