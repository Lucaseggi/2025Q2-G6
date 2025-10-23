"""RAG Service for orchestrating the retrieval pipeline"""

import json
import logging
from typing import Dict, Any, List, Optional

from src.clients.embedding import get_embedding
from src.clients.vectorial import search_vectors
from src.clients.relational import fetch_batch_entities
from src.services.llm_service import LLMAnswerService

logger = logging.getLogger(__name__)


class RAGService:
    """Service for orchestrating RAG pipeline: embed -> search -> fetch context -> generate answer"""

    def __init__(self, gemini_api_key: Optional[str] = None, gemini_model: str = "gemini-2.0-flash-lite"):
        """
        Initialize RAG service.

        Args:
            gemini_api_key: Gemini API key for LLM answer generation
            gemini_model: Gemini model name to use
        """
        self.llm_service = None
        if gemini_api_key:
            try:
                self.llm_service = LLMAnswerService(
                    api_key=gemini_api_key,
                    model_name=gemini_model
                )
                logger.info("LLM service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM service: {e}. Will return context without answer.")
        else:
            logger.warning("No Gemini API key provided. LLM answer generation will be disabled.")

    def get_context_for_question(
        self,
        question: str,
        filters: Optional[Dict[str, str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get relevant legal context for a user question.

        Args:
            question: The user's question
            filters: Optional metadata filters for vector search
            limit: Maximum number of results to retrieve

        Returns:
            Dict with:
                - success (bool): Whether the operation succeeded
                - context (dict): Contains normas_data and norma_ids
                - answer (str): Generated answer from LLM (empty if LLM unavailable)
                - message (str): Status message
        """
        try:
            # Step 1: Generate embedding for user question
            logger.info(f"Generating embedding for question: {question[:100]}...")
            embedding_result = get_embedding(question)

            if not embedding_result["success"] or not embedding_result["data"]:
                error_msg = f"Failed to generate embedding: {embedding_result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "context": {"normas_data": [], "norma_ids": []},
                    "answer": "",
                    "message": error_msg
                }

            embedding_vector = embedding_result["data"].get("embedding", [])
            logger.info(f"Successfully generated embedding with {len(embedding_vector)} dimensions")

            # Step 2: Search for similar vectors
            logger.info(f"Searching for similar vectors with limit={limit}")
            search_result = search_vectors(
                embedding=embedding_vector,
                filters=filters or {},
                limit=limit
            )

            if not search_result["success"]:
                error_msg = f"Vector search failed: {search_result.get('message', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "context": {"normas_data": [], "norma_ids": []},
                    "answer": "",
                    "message": error_msg
                }

            search_results = search_result.get("results", [])
            logger.info(f"Found {len(search_results)} similar documents")

            if not search_results:
                return {
                    "success": True,
                    "context": {"normas_data": [], "norma_ids": []},
                    "answer": "No documents found. Were they loaded?",
                    "message": "No similar documents found"
                }

            # Step 3: Extract unique norma IDs
            norma_ids = self._extract_norma_ids_from_search_results(search_results)
            logger.info(f"Extracted {len(norma_ids)} unique norma IDs: {norma_ids}")

            # Step 4: Fetch batch entities from relational microservice
            logger.info("Fetching batch entities from relational service")
            batch_result = fetch_batch_entities(search_results)

            if not batch_result["success"]:
                error_msg = f"Failed to fetch entities: {batch_result.get('message', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "context": {"normas_data": [], "norma_ids": norma_ids},
                    "message": error_msg
                }

            # Step 5: Parse normas JSON
            normas_json_str = batch_result["normas_json"]
            try:
                normas_data = json.loads(normas_json_str)
                logger.info(f"Successfully parsed {len(normas_data)} normas")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse normas_json: {e}")
                normas_data = []

            # Step 6: Generate answer using LLM
            answer = ""
            if self.llm_service and normas_data:
                logger.info("Generating answer using LLM")
                try:
                    llm_result = self.llm_service.generate_answer(
                        question=question,
                        context_data=normas_data
                    )
                    if llm_result["success"]:
                        answer = llm_result["answer"]
                        logger.info(f"Successfully generated answer with {llm_result.get('tokens_used', 0)} tokens")
                    else:
                        logger.warning(f"LLM failed to generate answer: {llm_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error calling LLM service: {e}")
            elif not self.llm_service:
                logger.info("LLM service not available, skipping answer generation")
            elif not normas_data:
                logger.info("No context data available, skipping answer generation")

            return {
                "success": True,
                "context": {
                    "normas_data": normas_data,
                    "norma_ids": norma_ids
                },
                "answer": answer,
                "message": f"Successfully retrieved context with {len(normas_data)} normas"
            }

        except Exception as e:
            error_msg = f"Unexpected error in RAG pipeline: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "context": {"normas_data": [], "norma_ids": []},
                "message": error_msg
            }

    def _extract_norma_ids_from_search_results(self, search_results: List[Dict]) -> List[int]:
        """
        Extract unique norma IDs from vector search results.

        Args:
            search_results: List of search result dicts with 'metadata' containing 'source_id'

        Returns:
            List of unique norma IDs (integers)
        """
        norma_ids = set()

        for result in search_results:
            metadata = result.get("metadata", {})
            source_id = metadata.get("source_id")

            if source_id is not None:
                try:
                    norma_id = int(source_id)
                    norma_ids.add(norma_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not convert source_id '{source_id}' to int: {e}")
                    continue

        return list(norma_ids)
