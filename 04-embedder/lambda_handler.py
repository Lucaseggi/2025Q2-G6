"""
AWS Lambda handler for embedder service

This is a thin adapter layer for SQS trigger only (no API endpoints).
Processes messages from embedding queue and sends to inserting queue.

All business logic remains in src/services - this handler only does message routing.
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

from models import ProcessedData
from structured_logger import StructuredLogger, LogStage

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.dependencies import get_embedder_service, get_queue_service
from src.config.settings import get_settings

# Initialize logger
logger = StructuredLogger("embedder", "lambda")

# Initialize services at cold start (reused across warm invocations)
_embedder_service = None
_queue_service = None
_settings = None


def get_services():
    """Initialize services on cold start, reuse on warm invocations"""
    global _embedder_service, _queue_service, _settings

    if _settings is None:
        logger.info("Cold start: Loading settings", stage=LogStage.STARTUP)
        _settings = get_settings()

    if _embedder_service is None:
        logger.info("Cold start: Initializing embedder service", stage=LogStage.STARTUP)
        _embedder_service = get_embedder_service()

        if not _embedder_service.is_available():
            logger.error("Embedder service not available", stage=LogStage.STARTUP)
            raise RuntimeError("Embedder service not available")

        logger.info("Embedder service initialized successfully", stage=LogStage.STARTUP)

    if _queue_service is None:
        logger.info("Cold start: Initializing queue service", stage=LogStage.STARTUP)
        _queue_service = get_queue_service()

    return _embedder_service, _queue_service, _settings


def handle_sqs_processing(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle SQS trigger: Process documents from embedding queue

    AWS automatically invokes Lambda when messages arrive in SQS queue.
    Generates embeddings and sends to inserting queue.

    Args:
        event: SQS event with Records array

    Returns:
        Processing summary
    """
    embedder_service, queue_service, settings = get_services()
    results = []

    for record in event.get('Records', []):
        norma_id = None
        try:
            # Parse message body
            message_body = json.loads(record['body'])

            # Handle cache wrapper format
            if 'cached_at' in message_body and 'data' in message_body:
                actual_data = message_body['data']
            else:
                actual_data = message_body

            # Parse ProcessedData
            input_data = ProcessedData.from_dict(actual_data)
            norma_id = input_data.scraping_data.infoleg_response.infoleg_id

            logger.log_message_received(
                queue_name='embedding',
                infoleg_id=norma_id
            )

            logger.info(
                f"Processing embeddings for norm {norma_id}",
                stage=LogStage.PROCESSING,
                infoleg_id=norma_id
            )

            # Process through embedder service
            processed_data = embedder_service.process_document(input_data)

            if processed_data:
                # Send to inserting queue
                output_queue = settings.sqs.queues.output
                success = queue_service.send_message(output_queue, processed_data.to_dict())

                if success:
                    logger.log_message_sent(
                        queue_name=output_queue,
                        infoleg_id=norma_id
                    )
                    results.append({
                        'norma_id': norma_id,
                        'status': 'success'
                    })
                    logger.info(
                        f"Successfully generated embeddings for norm {norma_id}",
                        stage=LogStage.PROCESSING,
                        infoleg_id=norma_id
                    )
                else:
                    results.append({
                        'norma_id': norma_id,
                        'status': 'failed',
                        'error': 'Failed to send to inserting queue'
                    })
                    logger.error(
                        f"Failed to send norm {norma_id} to inserting queue",
                        stage=LogStage.QUEUE_ERROR,
                        infoleg_id=norma_id
                    )
            else:
                results.append({
                    'norma_id': norma_id,
                    'status': 'failed',
                    'error': 'Embedder service returned None'
                })
                logger.error(
                    f"Failed to generate embeddings for norm {norma_id}",
                    stage=LogStage.PROCESSING,
                    infoleg_id=norma_id
                )

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()

            logger.error(
                f"Error processing SQS message: {type(e).__name__}: {str(e)}",
                stage=LogStage.PROCESSING,
                infoleg_id=norma_id,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=error_traceback[:500]
            )

            results.append({
                'norma_id': norma_id,
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


def handle_api_gateway_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle API Gateway events: /health and /embed endpoints

    Args:
        event: API Gateway event with httpMethod, path, body, etc.

    Returns:
        API Gateway response with statusCode, headers, and body
    """
    embedder_service, queue_service, settings = get_services()

    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    path = event.get('path', event.get('rawPath', '/'))

    logger.info(
        f"API Gateway request: {http_method} {path}",
        stage=LogStage.STARTUP,
        method=http_method,
        path=path
    )

    # Health endpoint
    if path == '/health' and http_method == 'GET':
        model_status = "available" if embedder_service.is_available() else "unavailable"

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'healthy',
                'service': 'embedding-ms',
                'embedding_model_status': model_status,
                'timestamp': datetime.now().isoformat()
            })
        }

    # Embed endpoint
    elif path == '/embed' and http_method == 'POST':
        try:
            # Parse request body
            body = json.loads(event.get('body', '{}'))
            text = body.get('text')

            if not text:
                logger.warning("Missing 'text' in request body", stage=LogStage.PROCESSING)
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Missing required field: text'})
                }

            logger.info(
                f"Generating embedding for text ({len(text)} chars)",
                stage=LogStage.PROCESSING
            )

            # Generate embedding
            embedding = embedder_service.embed_text(text)

            if embedding is None:
                logger.error("Failed to generate embedding", stage=LogStage.PROCESSING)
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Failed to generate embedding'})
                }

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'embedding': embedding,
                    'model': embedder_service.norm_embedder_service.get_model_name(),
                    'dimensions': len(embedding),
                    'timestamp': datetime.now().isoformat()
                })
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}", stage=LogStage.PROCESSING)
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()

            logger.error(
                f"Error processing /embed request: {type(e).__name__}: {str(e)}",
                stage=LogStage.PROCESSING,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=error_traceback[:500]
            )

            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            }

    # Unsupported endpoint
    else:
        logger.warning(
            f"Unsupported endpoint: {http_method} {path}",
            stage=LogStage.STARTUP
        )
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Endpoint not found: {http_method} {path}'})
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler: Routes between SQS events and API Gateway events

    Args:
        event: SQS event with Records array OR API Gateway event with httpMethod and path
        context: Lambda context object

    Returns:
        Processing summary for SQS or API Gateway response
    """
    logger.info(
        f"Lambda invoked",
        stage=LogStage.STARTUP,
        event_keys=list(event.keys()),
        request_id=context.aws_request_id if context else None
    )

    # Check if this is an API Gateway event
    if 'httpMethod' in event or ('requestContext' in event and 'http' in event.get('requestContext', {})):
        logger.info("Routing to API Gateway handler", stage=LogStage.STARTUP)
        return handle_api_gateway_event(event)

    # Validate SQS trigger
    if 'Records' not in event:
        logger.error("Invalid event: missing Records and not API Gateway", stage=LogStage.STARTUP)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid event: expected SQS trigger or API Gateway event'})
        }

    records = event.get('Records', [])
    if not records:
        logger.warning("No records in event", stage=LogStage.STARTUP)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No records to process'})
        }

    event_source = records[0].get('eventSource', '')
    if event_source != 'aws:sqs':
        logger.error(
            f"Unsupported event source: {event_source}",
            stage=LogStage.STARTUP
        )
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Unsupported event source: {event_source}'})
        }

    # Process SQS messages
    logger.info("Routing to SQS processing handler", stage=LogStage.STARTUP)
    return handle_sqs_processing(event)
