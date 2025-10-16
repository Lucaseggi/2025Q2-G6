import json
import os
import sys
import time
from datetime import datetime

from shared.rabbitmq_client import RabbitMQClient
from shared.models import ProcessedData
from shared.structured_logger import StructuredLogger, LogStage

# Force output flushing
import functools
print = functools.partial(print, flush=True)
from grpc_clients import GrpcServiceClients

logger = StructuredLogger("inserter", "worker")

def parse_numero_to_int(numero_str):
    """Parse numero field to integer, return -1 if unparseable"""
    if numero_str is None or numero_str == '':
        return -1

    try:
        # Remove any whitespace
        numero_str = str(numero_str).strip()
        # Try to parse as integer
        return int(numero_str)
    except (ValueError, TypeError):
        # If parsing fails, return -1
        return -1

def transform_id_normas(id_normas_list):
    """Transform id_normas list to have integer numero fields"""
    if not id_normas_list:
        return []

    transformed = []
    for item in id_normas_list:
        if isinstance(item, dict):
            transformed_item = item.copy()
            # Parse the numero field to integer
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
            # Priority: updated_text > original_text (matching purifier/processor logic)
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

def create_queue_client():
    return RabbitMQClient()

def main():
    logger.info("Inserter MS started - listening for messages", stage=LogStage.STARTUP)

    queue_client = create_queue_client()
    grpc_clients = GrpcServiceClients()

    while True:
        try:
            # Receive message from inserting queue
            message_body = queue_client.receive_message('inserting', timeout=20)

            if message_body:
                start_time = time.time()

                # Get document ID for logging
                try:
                    # Try new ProcessedData structure first
                    doc_id = message_body['scraping_data']['infoleg_response']['infoleg_id']
                except (KeyError, TypeError):
                    # Fallback to old structure for transition period
                    try:
                        doc_id = message_body['data']['norma']['infoleg_id']
                    except (KeyError, TypeError):
                        doc_id = "unknown"

                logger.log_message_received(
                    queue_name='inserting',
                    infoleg_id=doc_id
                )

                logger.log_processing_start(infoleg_id=doc_id)

                # Dump message_body to file for demo purposes
                # try:
                #     dump_path = f"message_dump_{doc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                #     with open(dump_path, 'w', encoding='utf-8') as f:
                #         json.dump(message_body, f, indent=2, ensure_ascii=False)
                #     print(f"[{datetime.now()}] Dumped message to {dump_path}")
                # except Exception as e:
                #     print(f"[{datetime.now()}] Warning: Could not dump message to file: {e}")

                # Transform data to legacy format for relational-guard
                legacy_format_data = transform_to_norma_format(message_body)

                # Call sequential pipeline: relational-guard → vectorial-guard
                # Note: relational-guard gets legacy format, vectorial-guard gets original format with embeddings
                logger.info(
                    "Inserting to databases",
                    stage=LogStage.INSERTION,
                    infoleg_id=doc_id
                )

                pipeline_result = grpc_clients.call_both_services_sequential(legacy_format_data)

                duration_ms = (time.time() - start_time) * 1000

                if pipeline_result['pipeline_success']:
                    logger.log_processing_complete(
                        infoleg_id=doc_id,
                        duration_ms=duration_ms,
                        relational_success=pipeline_result['relational']['success'],
                        vectorial_success=pipeline_result['vectorial']['success']
                    )
                else:
                    logger.log_processing_failed(
                        infoleg_id=doc_id,
                        error=f"Relational: {pipeline_result['relational']['message']}, Vectorial: {pipeline_result['vectorial']['message']}"
                    )

        except Exception as e:
            logger.error(
                f"Error in processing loop: {str(e)}",
                stage=LogStage.QUEUE_ERROR,
                error_type=type(e).__name__
            )

if __name__ == "__main__":
    main()