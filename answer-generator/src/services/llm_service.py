"""Minimal LLM service for answer generation using Gemini API"""

import logging
from typing import Dict, Any, List

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class LLMAnswerService:
    """Minimal LLM service for generating answers based on legal context"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-lite", max_retries: int = 3):
        """
        Initialize LLM service.

        Args:
            api_key: Gemini API key
            model_name: Name of the Gemini model to use
            max_retries: Maximum number of retries for API calls
        """
        if not api_key:
            raise ValueError("Gemini API key is required")

        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries

        # Configure Gemini with API key
        genai.configure(api_key=self.api_key)
        logger.info(f"Initialized LLM service with model: {model_name}")

    def generate_answer(
        self,
        question: str,
        context_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an answer using Gemini based on the question and context.

        Args:
            question: The user's question
            context_data: List of normas data retrieved from the RAG pipeline

        Returns:
            dict with:
                - success (bool): Whether the operation succeeded
                - answer (str): The generated answer
                - error (str): Error message if failed
                - tokens_used (int): Number of tokens used
        """
        try:
            # Format context for the LLM
            context_text = self._format_context(context_data)

            # Create the system prompt
            system_prompt = """Eres un asistente legal experto que ayuda a responder preguntas sobre leyes y normativas argentinas.
Tu trabajo es proporcionar respuestas claras, precisas y útiles basadas en el contexto legal proporcionado.

Instrucciones:
- Basa tu respuesta únicamente en el contexto proporcionado
- Si el contexto no contiene información suficiente para responder la pregunta, indícalo claramente
- Cita las normas relevantes (tipo de norma, título) cuando sea apropiado
- Sé conciso pero completo
- Usa un lenguaje claro y profesional en español"""

            # Create the user message with question and context
            user_message = f"""Pregunta: {question}

Contexto legal relevante:
{context_text}

Por favor, proporciona una respuesta basada en este contexto."""

            # Call Gemini API with retries
            result = self._call_gemini_with_retries(
                system_prompt=system_prompt,
                user_message=user_message
            )

            return result

        except Exception as e:
            error_msg = f"Unexpected error generating answer: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "answer": "",
                "error": error_msg,
                "tokens_used": 0
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def _call_gemini_with_retries(
        self,
        system_prompt: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Call Gemini API with retries.

        Args:
            system_prompt: System instruction for the model
            user_message: User message with question and context

        Returns:
            dict with success, answer, error, and tokens_used
        """
        try:
            logger.info(f"Calling Gemini API with model: {self.model_name}")

            # Create the model with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt
            )

            # Configure generation parameters
            gen_config = genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.3,
                top_p=0.8
            )

            # Make the API call
            response = model.generate_content(
                user_message,
                generation_config=gen_config
            )

            if not response.text:
                raise ValueError("Empty response from Gemini API")

            # Get token usage
            tokens_used = 0
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    if hasattr(response.usage_metadata, 'total_token_count'):
                        tokens_used = response.usage_metadata.total_token_count
                    elif hasattr(response.usage_metadata, 'totalTokenCount'):
                        tokens_used = response.usage_metadata.totalTokenCount
            except Exception as e:
                logger.warning(f"Could not extract token count: {e}")
                tokens_used = 0

            logger.info(f"Successfully generated answer with {len(response.text)} characters, {tokens_used} tokens")

            return {
                "success": True,
                "answer": response.text,
                "error": None,
                "tokens_used": tokens_used
            }

        except Exception as e:
            error_msg = f"Gemini API call failed: {str(e)}"
            logger.error(error_msg)
            raise  # Re-raise for retry mechanism

    def _format_context(self, context_data: List[Dict[str, Any]]) -> str:
        """
        Format the context data into a readable string for the LLM.

        Args:
            context_data: List of normas data

        Returns:
            Formatted context string
        """
        if not context_data:
            return "No se encontró contexto relevante."

        formatted_parts = []

        for idx, norma in enumerate(context_data, 1):
            # Extract key information
            tipo_norma = norma.get("tipo_norma", "N/A")
            titulo = norma.get("titulo_resumido") or norma.get("titulo_sumario", "Sin título")
            jurisdiccion = norma.get("jurisdiccion", "N/A")
            texto_resumido = norma.get("texto_resumido", "")

            # Build norma section
            norma_text = f"\n--- Norma {idx} ---\n"
            norma_text += f"Tipo: {tipo_norma}\n"
            norma_text += f"Título: {titulo}\n"
            norma_text += f"Jurisdicción: {jurisdiccion}\n"

            if texto_resumido:
                norma_text += f"Resumen: {texto_resumido}\n"

            # Include articles if available
            articles = norma.get("articles", [])
            if articles:
                norma_text += "\nArtículos relevantes:\n"
                for article in articles[:10]:  # Limit to first 10 articles to avoid context overflow
                    ordinal = article.get("ordinal", "N/A")
                    body = article.get("body", "")
                    if body:
                        norma_text += f"  • Artículo {ordinal}: {body}\n"

            formatted_parts.append(norma_text)

        return "\n".join(formatted_parts)
