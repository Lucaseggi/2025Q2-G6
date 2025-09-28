import json
import os
import sys
from datetime import datetime

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient
from grpc_clients import GrpcServiceClients

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
                doc_id = message_body['data']['norma']['infoleg_id']
                print(f"[{datetime.now()}] Received message for norma {doc_id}")

                # Call sequential pipeline: relational-ms → vectorial-ms
                pipeline_result = grpc_clients.call_both_services_sequential(message_body)

                print(f"[{datetime.now()}] === Pipeline Results for norma {doc_id} ===")
                print(f"[{datetime.now()}] Relational MS: {'SUCCESS' if pipeline_result['relational']['success'] else 'FAILED'} - {pipeline_result['relational']['message']}")
                print(f"[{datetime.now()}] Vectorial MS: {'SUCCESS' if pipeline_result['vectorial']['success'] else 'FAILED'} - {pipeline_result['vectorial']['message']}")
                print(f"[{datetime.now()}] Pipeline: {'SUCCESS' if pipeline_result['pipeline_success'] else 'FAILED'}")
                print(f"[{datetime.now()}] =============================================")

        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()