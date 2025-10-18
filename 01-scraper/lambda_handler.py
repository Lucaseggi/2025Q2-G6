"""
AWS Lambda handler for scraper service

This is a thin adapter layer that exposes HTTP endpoints via API Gateway:
- POST /scrape: Scrape a norm and send to purifying queue (with cache support)
- POST /replay: Replay a cached norm to purifying queue
- GET /health: Health check

All business logic remains in src/services - this handler only does routing.
"""

import json
import logging
import os
import sys
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/var/task/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from structured_logger import StructuredLogger, LogStage

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.dependencies import get_scraper_service

# Initialize logger
logger = StructuredLogger("scraper", "lambda")

# Initialize services at cold start (reused across warm invocations)
_scraper_service = None


def get_services():
    """Initialize services on cold start, reuse on warm invocations"""
    global _scraper_service

    if _scraper_service is None:
        logger.info("Cold start: Initializing scraper service", stage=LogStage.STARTUP)
        _scraper_service = get_scraper_service()

    return _scraper_service


def handle_scrape(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /scrape: Scrape norm and send to queue

    This endpoint:
    1. Checks cache first (unless force=True)
    2. If cache hit: sends cached data to queue
    3. If cache miss: scrapes from InfoLeg API, caches, sends to queue

    Request body:
    {
        "infoleg_id": 123456,
        "force": false  # optional, default false
    }

    Returns:
        API Gateway proxy response
    """
    try:
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'status': 'error',
                        'message': 'Invalid JSON body'
                    })
                }

        # Extract query parameters (support both body and query string)
        query_params = event.get('queryStringParameters') or {}
        infoleg_id = body.get('infoleg_id') or query_params.get('infoleg_id')
        force = body.get('force', False) or (query_params.get('force', 'false').lower() == 'true')

        # Validate required parameters
        if not infoleg_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Missing required parameter: infoleg_id'
                })
            }

        # Convert to integer
        try:
            infoleg_id = int(infoleg_id)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Invalid infoleg_id: must be an integer'
                })
            }

        logger.info(
            f"Scrape request for norm {infoleg_id} (force={force})",
            stage=LogStage.PROCESSING,
            infoleg_id=infoleg_id,
            force=force
        )

        # Call scraper service
        scraper_service = get_services()
        success, source = scraper_service.scrape_specific_norm(infoleg_id, force=force)

        if success:
            is_cache_hit = source == 'cache'
            status = 'cached' if is_cache_hit else 'success'
            message = (
                f'Norm {infoleg_id} served from cache and sent to queue'
                if is_cache_hit
                else f'Successfully scraped norm {infoleg_id} and sent to queue'
            )

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': status,
                    'message': message,
                    'infoleg_id': infoleg_id,
                    'source': source,
                    'cache_hit': is_cache_hit,
                    'forced': force
                })
            }
        else:
            # Determine status code based on error
            status_code = 404 if 'not_found' in source else 500

            return {
                'statusCode': status_code,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Failed to scrape norm {infoleg_id}',
                    'reason': source,
                    'infoleg_id': infoleg_id
                })
            }

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()

        logger.error(
            f"Error in scrape handler: {type(e).__name__}: {str(e)}",
            stage=LogStage.PROCESSING,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=error_traceback[:500]
        )

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': 'Internal server error',
                'error': str(e)
            })
        }


def handle_replay(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /replay: Replay cached norm to queue

    This endpoint:
    1. Fetches norm from cache
    2. Sends to purifying queue
    3. Returns error if not in cache

    Request body:
    {
        "infoleg_id": 123456,
        "force": false  # optional, ignored for replay
    }

    Returns:
        API Gateway proxy response
    """
    try:
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'status': 'error',
                        'message': 'Invalid JSON body'
                    })
                }

        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        infoleg_id = body.get('infoleg_id') or query_params.get('infoleg_id')
        force = body.get('force', False) or (query_params.get('force', 'false').lower() == 'true')

        # Validate required parameters
        if not infoleg_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Missing required parameter: infoleg_id'
                })
            }

        # Convert to integer
        try:
            infoleg_id = int(infoleg_id)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Invalid infoleg_id: must be an integer'
                })
            }

        logger.info(
            f"Replay request for norm {infoleg_id}",
            stage=LogStage.PROCESSING,
            infoleg_id=infoleg_id
        )

        # Call scraper service
        scraper_service = get_services()
        success, source = scraper_service.replay_norm(infoleg_id, force=force)

        if success:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'success',
                    'message': f'Successfully replayed norm {infoleg_id} to purifying queue',
                    'infoleg_id': infoleg_id,
                    'cache_hit': True
                })
            }
        else:
            # Determine status code
            status_code = 404 if 'cache_miss' in source else 500

            return {
                'statusCode': status_code,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Failed to replay norm {infoleg_id}',
                    'reason': source,
                    'infoleg_id': infoleg_id
                })
            }

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()

        logger.error(
            f"Error in replay handler: {type(e).__name__}: {str(e)}",
            stage=LogStage.PROCESSING,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=error_traceback[:500]
        )

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': 'Internal server error',
                'error': str(e)
            })
        }


def handle_health_check(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle GET /health: Health check

    Returns:
        API Gateway proxy response
    """
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy',
            'service': 'scraper',
            'version': '2.0.0',
            'lambda': True
        })
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler: Routes API Gateway requests

    Supported endpoints:
    - GET /health: Health check
    - POST /scrape: Scrape norm and send to queue (with cache)
    - POST /replay: Replay cached norm to queue

    Args:
        event: API Gateway proxy event
        context: Lambda context object

    Returns:
        API Gateway proxy response with statusCode, headers, body
    """
    logger.info(
        f"Lambda invoked",
        stage=LogStage.STARTUP,
        method=event.get('httpMethod'),
        path=event.get('path'),
        request_id=context.request_id if context else None
    )

    # Route based on path and method
    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # Health check
    if path == '/health' and method == 'GET':
        return handle_health_check(event)

    # Scrape endpoint (scrape + send to queue)
    elif path == '/scrape' and method == 'POST':
        return handle_scrape(event)

    # Replay endpoint (from cache to queue)
    elif path == '/replay' and method == 'POST':
        return handle_replay(event)

    # Unknown endpoint
    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': f'Endpoint not found: {method} {path}',
                'available_endpoints': [
                    'GET /health',
                    'POST /scrape',
                    'POST /replay'
                ]
            })
        }
