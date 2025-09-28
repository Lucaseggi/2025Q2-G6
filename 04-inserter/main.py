import json
import os
import sys
from datetime import datetime

from shared.rabbitmq_client import RabbitMQClient
from shared.models import ProcessedData

# Force output flushing
import functools
print = functools.partial(print, flush=True)
from grpc_clients import GrpcServiceClients

def transform_to_legacy_format(message_body):
    """Transform new ProcessedData format to legacy format expected by relational-ms"""
    try:
        # Extract data from the new format
        scraping_data = message_body.get('scraping_data', {})
        infoleg_response = scraping_data.get('infoleg_response', {})
        processing_data = message_body.get('processing_data', {})

        # Build norma object in the format expected by relational-ms
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

            # Add structured text from parsings
            original_parsing = parsings.get('original_text', {})
            if original_parsing and 'structured_data' in original_parsing:
                norma['structured_texto_norma'] = original_parsing['structured_data']

        # Return in the format expected by relational-ms
        return {
            'data': {
                'norma': norma
            }
        }

    except Exception as e:
        print(f"[{datetime.now()}] Error transforming data format: {e}")
        return message_body  # Return original if transformation fails

def create_queue_client():
    return RabbitMQClient()

def main():
    print("Inserter MS started - listening for messages...")

    queue_client = create_queue_client()
    grpc_clients = GrpcServiceClients()

    while True:
        try:
            # Receive message from inserting queue
            message_body = queue_client.receive_message('inserting', timeout=20)


            if message_body:
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
                print(f"[{datetime.now()}] Received message for norma {doc_id}")

                # Transform data to legacy format for relational-ms
                legacy_format_data = transform_to_legacy_format(message_body)

                # Call sequential pipeline: relational-ms → vectorial-ms
                # Note: relational-ms gets legacy format, vectorial-ms gets original format with embeddings
                pipeline_result = grpc_clients.call_both_services_sequential(legacy_format_data, message_body)

                print(f"[{datetime.now()}] === Pipeline Results for norma {doc_id} ===")
                print(f"[{datetime.now()}] Relational MS: {'SUCCESS' if pipeline_result['relational']['success'] else 'FAILED'} - {pipeline_result['relational']['message']}")
                print(f"[{datetime.now()}] Vectorial MS: {'SUCCESS' if pipeline_result['vectorial']['success'] else 'FAILED'} - {pipeline_result['vectorial']['message']}")
                print(f"[{datetime.now()}] Pipeline: {'SUCCESS' if pipeline_result['pipeline_success'] else 'FAILED'}")
                print(f"[{datetime.now()}] =============================================")

        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()