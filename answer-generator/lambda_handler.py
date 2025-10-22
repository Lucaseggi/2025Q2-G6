"""
AWS Lambda handler for answer generator service

This handler supports API Gateway events for /health and /question endpoints.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/var/task/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.dependencies import get_rag_service
from src.config.settings import get_settings

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services at cold start (reused across warm invocations)
_rag_service = None
_settings = None

# CORS headers for all responses
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Requested-With',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}


def get_services():
    """Initialize services on cold start, reuse on warm invocations"""
    global _rag_service, _settings

    if _settings is None:
        logger.info("Cold start: Loading settings")
        _settings = get_settings()

    if _rag_service is None:
        logger.info("Cold start: Initializing RAG service")
        _rag_service = get_rag_service()

    return _rag_service, _settings


def handle_health_check() -> Dict[str, Any]:
    """
    Handle health check endpoint

    Returns:
        API Gateway response with health status
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            **CORS_HEADERS
        },
        'body': json.dumps({
            'status': 'healthy',
            'service': 'answer-generator',
            'timestamp': datetime.now().isoformat(),
            'dependencies': {
                'embedder': 'not_checked',
                'vectorial_guard': 'not_checked',
                'relational_guard': 'not_checked'
            }
        })
    }


def handle_question(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle question endpoint

    Args:
        event: API Gateway event with request body

    Returns:
        API Gateway response with context
    """
    rag_service, settings = get_services()

    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        question = body.get('question')
        filters = body.get('filters')
        limit = body.get('limit', settings.default_search_limit)

        if not question:
            logger.warning("Missing 'question' in request body")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    **CORS_HEADERS
                },
                'body': json.dumps({'error': 'Missing required field: question'})
            }

        logger.info(f"Processing question: {question[:100]}...")

        # Get context from RAG service
        result = rag_service.get_context_for_question(
            question=question,
            filters=filters,
            limit=limit
        )

        if not result["success"]:
            logger.error(f"RAG pipeline failed: {result.get('message')}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    **CORS_HEADERS
                },
                'body': json.dumps({
                    'error': result.get('message', 'Failed to retrieve context')
                })
            }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                **CORS_HEADERS
            },
            'body': json.dumps({
                'success': True,
                'question': question,
                'context': result['context'],
                'answer': result.get('answer', ''),
                'message': result['message'],
                'timestamp': datetime.now().isoformat()
            })
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                **CORS_HEADERS
            },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()

        logger.error(f"Error processing question: {type(e).__name__}: {str(e)}")
        logger.debug(error_traceback)

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                **CORS_HEADERS
            },
            'body': json.dumps({
                'error': str(e),
                'error_type': type(e).__name__
            })
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler: Routes API Gateway events

    Args:
        event: API Gateway event with httpMethod and path
        context: Lambda context object

    Returns:
        API Gateway response
    """
    logger.info(
        f"Lambda invoked",
        extra={
            'event_keys': list(event.keys()),
            'request_id': context.aws_request_id if context else None
        }
    )

    # Extract HTTP method and path
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    path = event.get('path', event.get('rawPath', '/'))

    logger.info(f"API Gateway request: {http_method} {path}")

    # Handle OPTIONS requests for CORS preflight
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    # Route to appropriate handler
    if path == '/health' and http_method == 'GET':
        return handle_health_check()
    elif path == '/question' and http_method == 'POST':
        return handle_question(event)
    else:
        logger.warning(f"Unsupported endpoint: {http_method} {path}")
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                **CORS_HEADERS
            },
            'body': json.dumps({'error': f'Endpoint not found: {http_method} {path}'})
        }
