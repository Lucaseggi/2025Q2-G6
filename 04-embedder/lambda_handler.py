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
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/var/task/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from models import ProcessedData
from structured_logger import StructuredLogger, LogStage

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dependencies import get_embedder_service

# Initialize logger
logger = StructuredLogger("embedder", "lambda")

# Initialize services at cold start (reused across warm invocations)
_embedder_service = None


def get_services():
    """Initialize services on cold start, reuse on warm invocations"""
    global _embedder_service

    if _embedder_service is None:
        logger.info("Cold start: Initializing embedder service", stage=LogStage.STARTUP)
        _embedder_service = get_embedder_service()

        if not _embedder_service.is_available():
            logger.error("Embedder service not available", stage=LogStage.STARTUP)
            raise RuntimeError("Embedder service not available")

        logger.info("Embedder service initialized successfully", stage=LogStage.STARTUP)

    return _embedder_service


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
    embedder_service = get_services()
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


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler: Processes SQS events only

    Args:
        event: SQS event with Records array
        context: Lambda context object

    Returns:
        Processing summary
    """
    logger.info(
        f"Lambda invoked",
        stage=LogStage.STARTUP,
        event_keys=list(event.keys()),
        request_id=context.request_id if context else None
    )

    # Validate SQS trigger
    if 'Records' not in event:
        logger.error("Invalid event: missing Records", stage=LogStage.STARTUP)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid event: expected SQS trigger'})
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
