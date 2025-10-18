"""
AWS Lambda handler for processor service

This is a thin adapter layer that routes between two invocation modes:
1. SQS Trigger: Automatic invocation when messages arrive in processing queue
2. API Gateway Trigger: HTTP endpoint for cache replay functionality

All business logic remains in src/services - this handler only does routing.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

# Add shared modules to path
sys.path.append('/var/task/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from models import ProcessedData
from structured_logger import StructuredLogger, LogStage

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.dependencies import get_parsing_service, get_cache_replay_service

# Initialize logger
logger = StructuredLogger("processor", "lambda")

# Initialize services at cold start (reused across warm invocations)
_parsing_service = None
_cache_replay_service = None


def get_services():
    """Initialize services on cold start, reuse on warm invocations"""
    global _parsing_service, _cache_replay_service

    if _parsing_service is None:
        logger.info("Cold start: Initializing parsing service", stage=LogStage.STARTUP)
        _parsing_service = get_parsing_service()

    if _cache_replay_service is None:
        logger.info("Cold start: Initializing cache replay service", stage=LogStage.STARTUP)
        _cache_replay_service = get_cache_replay_service()

    return _parsing_service, _cache_replay_service


def handle_sqs_processing(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle SQS trigger: Force processing through full pipeline

    AWS automatically invokes Lambda when messages arrive in SQS queue.
    No manual polling needed - SQS integration handles:
    - Polling the queue
    - Batching messages
    - Retries on failure
    - Message deletion on success

    Args:
        event: SQS event with Records array

    Returns:
        Processing summary (not HTTP response)
    """
    parsing_service, _ = get_services()
    results = []

    for record in event.get('Records', []):
        infoleg_id = None
        try:
            # Parse message body
            message_body = json.loads(record['body'])

            # Handle cache wrapper format if present
            if 'cached_at' in message_body and 'data' in message_body:
                actual_data = message_body['data']
            else:
                actual_data = message_body

            # Convert to ProcessedData
            input_data = ProcessedData.from_dict(actual_data)
            infoleg_id = input_data.scraping_data.infoleg_response.infoleg_id

            logger.log_message_received(
                queue_name='processing',
                infoleg_id=infoleg_id
            )

            logger.info(
                f"Processing document {infoleg_id} from SQS (force mode)",
                stage=LogStage.PROCESSING,
                infoleg_id=infoleg_id
            )

            # Process through full pipeline (force=True, bypasses cache)
            processed_data = parsing_service.process_document(input_data)

            if processed_data:
                results.append({
                    'infoleg_id': infoleg_id,
                    'status': 'success'
                })
                logger.info(
                    f"Successfully processed document {infoleg_id}",
                    stage=LogStage.PROCESSING,
                    infoleg_id=infoleg_id
                )
            else:
                results.append({
                    'infoleg_id': infoleg_id,
                    'status': 'failed',
                    'error': 'Processing pipeline returned None'
                })
                logger.error(
                    f"Failed to process document {infoleg_id}",
                    stage=LogStage.PROCESSING,
                    infoleg_id=infoleg_id
                )

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()

            logger.error(
                f"Error processing SQS message: {type(e).__name__}: {str(e)}",
                stage=LogStage.PROCESSING,
                infoleg_id=infoleg_id,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=error_traceback[:500]
            )

            results.append({
                'infoleg_id': infoleg_id,
                'status': 'error',
                'error_type': type(e).__name__,
                'error': str(e)
            })

            # Re-raise to trigger SQS retry mechanism
            raise

    # Return processing summary
    return {
        'statusCode': 200,
        'processed': len(results),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] != 'success']),
        'results': results
    }


def handle_api_replay(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle API Gateway trigger: Replay from S3 cache

    API Gateway invokes Lambda with HTTP request details.
    Must return proper API Gateway proxy response format:
    {
        "statusCode": 200,
        "headers": {...},
        "body": "..." (JSON string)
    }

    Args:
        event: API Gateway proxy event

    Returns:
        API Gateway proxy response
    """
    try:
        # Parse request parameters
        query_params = event.get('queryStringParameters') or {}
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

        # Get parameters (prefer body over query string)
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
            f"API replay request for norm {infoleg_id} (force={force})",
            stage=LogStage.PROCESSING,
            infoleg_id=infoleg_id,
            force=force
        )

        # Use cache replay service
        _, cache_replay_service = get_services()
        success, source = cache_replay_service.replay_norm(infoleg_id, force=force)

        if success:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'success',
                    'message': f'Successfully replayed norm {infoleg_id} to embedding queue',
                    'infoleg_id': infoleg_id,
                    'source': source,
                    'cache_hit': True
                })
            }
        else:
            # Determine appropriate status code based on source
            status_code = 404 if source == 'not_in_cache' else 500

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
            f"Error in API replay handler: {type(e).__name__}: {str(e)}",
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
    Handle health check requests

    Args:
        event: API Gateway proxy event

    Returns:
        API Gateway proxy response
    """
    parsing_service, _ = get_services()

    is_available = parsing_service.is_available()

    return {
        'statusCode': 200 if is_available else 503,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy' if is_available else 'unhealthy',
            'service': 'processor',
            'version': '1.0.0',
            'lambda': True
        })
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler: Routes requests based on trigger source

    Trigger detection:
    - SQS: event contains 'Records' with eventSource='aws:sqs'
    - API Gateway: event contains 'httpMethod' and 'path'

    Args:
        event: Lambda event (structure varies by trigger)
        context: Lambda context object

    Returns:
        Response format varies by trigger:
        - SQS: Processing summary dict
        - API Gateway: Proxy response with statusCode, headers, body
    """
    logger.info(
        f"Lambda invoked - trigger detection",
        stage=LogStage.STARTUP,
        event_keys=list(event.keys()),
        request_id=context.request_id if context else None
    )

    # Route 1: SQS Trigger
    if 'Records' in event:
        records = event.get('Records', [])
        if records:
            event_source = records[0].get('eventSource', '')

            if event_source == 'aws:sqs':
                logger.info("Routing to SQS processing handler", stage=LogStage.STARTUP)
                return handle_sqs_processing(event)
            else:
                logger.error(
                    f"Unsupported event source in Records: {event_source}",
                    stage=LogStage.STARTUP
                )
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Unsupported event source: {event_source}'
                    })
                }

    # Route 2: API Gateway Trigger
    elif 'httpMethod' in event:
        path = event.get('path', '')
        method = event.get('httpMethod', '')

        logger.info(
            f"Routing to API handler: {method} {path}",
            stage=LogStage.STARTUP,
            method=method,
            path=path
        )

        # Health check endpoint
        if path == '/health' and method == 'GET':
            return handle_health_check(event)

        # Replay endpoint
        elif path == '/replay' and method == 'POST':
            return handle_api_replay(event)

        # Unknown endpoint
        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Endpoint not found: {method} {path}'
                })
            }

    # Route 3: Unknown trigger
    else:
        logger.error(
            "Unknown event type - cannot route",
            stage=LogStage.STARTUP,
            event_sample=str(event)[:200]
        )

        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': 'Unknown event type - expected SQS or API Gateway trigger'
            })
        }
