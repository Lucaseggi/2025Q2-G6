"""
AWS Lambda handler for inserter service

This is a thin adapter layer for SQS trigger only (no API endpoints).
Processes messages from inserting queue and inserts into relational and vectorial databases.

All business logic remains in worker.py - this handler delegates to it.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/var/task/shared')
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from models import ProcessedData
from structured_logger import StructuredLogger, LogStage

# Add local modules to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from grpc_clients import GrpcServiceClients

# Initialize logger
logger = StructuredLogger("inserter", "lambda")

# Initialize gRPC clients at cold start (reused across warm invocations)
_grpc_clients = None


def get_grpc_clients():
    """Initialize gRPC clients on cold start, reuse on warm invocations"""
    global _grpc_clients

    if _grpc_clients is None:
        logger.info("Cold start: Initializing gRPC clients", stage=LogStage.STARTUP)
        _grpc_clients = GrpcServiceClients()
        logger.info("gRPC clients initialized successfully", stage=LogStage.STARTUP)

    return _grpc_clients


def parse_numero_to_int(numero_str):
    """Parse numero field to integer, return -1 if unparseable"""
    if numero_str is None or numero_str == '':
        return -1

    try:
        numero_str = str(numero_str).strip()
        return int(numero_str)
    except (ValueError, TypeError):
        return -1


def transform_id_normas(id_normas_list):
    """Transform id_normas list to have integer numero fields"""
    if not id_normas_list:
        return []

    transformed = []
    for item in id_normas_list:
        if isinstance(item, dict):
            transformed_item = item.copy()
            transformed_item['numero'] = parse_numero_to_int(item.get('numero'))
            transformed.append(transformed_item)
        else:
            transformed.append(item)

    return transformed


def transform_to_norma_format(message_body):
    """Transform new ProcessedData format to legacy format expected by relational-guard"""
    try:
        # Extract data from the new format
        scraping_data = message_body.get('scraping_data', {})
        infoleg_response = scraping_data.get('infoleg_response', {})
        processing_data = message_body.get('processing_data', {})

        # Build norma object in the format expected by relational-guard
        norma = {
            # Basic infoleg fields
            'infoleg_id': infoleg_response.get('infoleg_id'),
            'jurisdiccion': infoleg_response.get('jurisdiccion'),
            'clase_norma': infoleg_response.get('clase_norma'),
            'tipo_norma': infoleg_response.get('tipo_norma'),
            'sancion': infoleg_response.get('sancion'),
            'publicacion': infoleg_response.get('publicacion'),
            'titulo_sumario': infoleg_response.get('titulo_sumario'),
            'titulo_resumido': infoleg_response.get('titulo_resumido'),
            'observaciones': infoleg_response.get('observaciones'),
            'nro_boletin': infoleg_response.get('nro_boletin'),
            'pag_boletin': infoleg_response.get('pag_boletin'),
            'texto_resumido': infoleg_response.get('texto_resumido'),
            'texto_norma': infoleg_response.get('texto_norma'),
            'texto_norma_actualizado': infoleg_response.get('texto_norma_actualizado'),
            'estado': infoleg_response.get('estado'),
            # Referencias and relaciones (with numero parsing)
            'id_normas': transform_id_normas(infoleg_response.get('id_normas', [])),
            'lista_normas_que_complementa': infoleg_response.get('lista_normas_que_complementa', []),
            'lista_normas_que_la_complementan': infoleg_response.get('lista_normas_que_la_complementan', []),
        }

        # Add processing data if available
        if processing_data:
            purifications = processing_data.get('purifications', {})
            parsings = processing_data.get('parsings', {})
            processor_metadata = processing_data.get('processor_metadata', {})
            embedder_metadata = processing_data.get('embedder_metadata', {})

            # Add purified text
            norma['purified_texto_norma'] = purifications.get('original_text', '')
            norma['purified_texto_norma_actualizado'] = purifications.get('updated_text', '')

            # Add LLM metadata
            norma['llm_model_used'] = processor_metadata.get('model_used')
            norma['llm_tokens_used'] = processor_metadata.get('tokens_used')

            # Add embedding metadata
            norma['embedding_model'] = embedder_metadata.get('embedding_model_used')
            norma['embedded_at'] = embedder_metadata.get('embedding_timestamp')

            # Add summarized text embedding
            summarized_text_embedding = processing_data.get('summarized_text_embedding')
            if summarized_text_embedding:
                norma['summarized_text_embedding'] = summarized_text_embedding

            # Add structured text from parsings
            updated_parsing = parsings.get('updated_text', {})
            original_parsing = parsings.get('original_text', {})

            if updated_parsing and 'structured_data' in updated_parsing:
                norma['structured_texto_norma'] = updated_parsing['structured_data']
            elif original_parsing and 'structured_data' in original_parsing:
                norma['structured_texto_norma'] = original_parsing['structured_data']

        # Return in the format expected by relational-guard
        return {
            'data': {
                'norma': norma
            }
        }

    except Exception as e:
        logger.error(
            f"Error transforming data format: {str(e)}",
            stage=LogStage.DATA_TRANSFORMATION,
            error_type=type(e).__name__
        )
        return message_body  # Return original if transformation fails


def handle_sqs_processing(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle SQS trigger: Insert documents into databases

    AWS automatically invokes Lambda when messages arrive in SQS queue.
    Inserts data into both relational and vectorial databases via gRPC.

    Args:
        event: SQS event with Records array

    Returns:
        Processing summary
    """
    grpc_clients = get_grpc_clients()
    results = []

    for record in event.get('Records', []):
        doc_id = None
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            start_time = time.time()

            # Get document ID for logging
            try:
                doc_id = message_body['scraping_data']['infoleg_response']['infoleg_id']
            except (KeyError, TypeError):
                try:
                    doc_id = message_body['data']['norma']['infoleg_id']
                except (KeyError, TypeError):
                    doc_id = "unknown"

            logger.log_message_received(
                queue_name='inserting',
                infoleg_id=doc_id
            )

            logger.log_processing_start(infoleg_id=doc_id)

            # Transform data to legacy format for relational-guard
            legacy_format_data = transform_to_norma_format(message_body)

            # Call sequential pipeline: relational-guard → vectorial-guard
            logger.info(
                "Inserting to databases",
                stage=LogStage.INSERTION,
                infoleg_id=doc_id
            )

            pipeline_result = grpc_clients.call_both_services_sequential(legacy_format_data)

            duration_ms = (time.time() - start_time) * 1000

            if pipeline_result['pipeline_success']:
                results.append({
                    'doc_id': doc_id,
                    'status': 'success',
                    'relational_success': pipeline_result['relational']['success'],
                    'vectorial_success': pipeline_result['vectorial']['success']
                })

                logger.log_processing_complete(
                    infoleg_id=doc_id,
                    duration_ms=duration_ms,
                    relational_success=pipeline_result['relational']['success'],
                    vectorial_success=pipeline_result['vectorial']['success']
                )
            else:
                results.append({
                    'doc_id': doc_id,
                    'status': 'failed',
                    'relational_message': pipeline_result['relational']['message'],
                    'vectorial_message': pipeline_result['vectorial']['message']
                })

                logger.log_processing_failed(
                    infoleg_id=doc_id,
                    error=f"Relational: {pipeline_result['relational']['message']}, Vectorial: {pipeline_result['vectorial']['message']}"
                )

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()

            logger.error(
                f"Error processing SQS message: {type(e).__name__}: {str(e)}",
                stage=LogStage.PROCESSING,
                infoleg_id=doc_id,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=error_traceback[:500]
            )

            results.append({
                'doc_id': doc_id,
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
        request_id=context.aws_request_id if context else None
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
