import json
import os
import sys
import requests
from datetime import datetime

sys.path.append('/app/shared')
from rabbitmq_client import RabbitMQClient
from models import ProcessedData

# Force output flushing
import functools
print = functools.partial(print, flush=True)

def create_queue_client():
    return RabbitMQClient()


def main():
    print("Inserter MS started - listening for messages and printing them...")
    print("Note: This inserter now only prints received packages, no API calls are made.")

    try:
        queue_client = create_queue_client()
        print("RabbitMQ client created successfully!")
    except Exception as e:
        print(f"FAILED to create RabbitMQ client: {e}")
        return

    while True:
        try:
            # Receive message from inserting queue
            message_body = queue_client.receive_message('inserting', timeout=20)

            if message_body:
                print(f"[{datetime.now()}] Inserter: Received message")

                # Show the complete structure but collapse embeddings
                try:
                    def collapse_embeddings_recursive(obj):
                        if isinstance(obj, dict):
                            result = {}
                            for key, value in obj.items():
                                if key == 'embedding' and isinstance(value, list):
                                    result[key] = f"[EMBEDDING_VECTOR_{len(value)}_DIMS]"
                                else:
                                    result[key] = collapse_embeddings_recursive(value)
                            return result
                        elif isinstance(obj, list):
                            return [collapse_embeddings_recursive(item) for item in obj]
                        else:
                            return obj

                    collapsed_message = collapse_embeddings_recursive(message_body)
                    print(json.dumps(collapsed_message, indent=2, default=str))

                except Exception as parse_error:
                    print(f"[{datetime.now()}] Inserter: Error parsing ProcessedData: {parse_error}")
                    print("Raw message:")
                    print(json.dumps(message_body, indent=2, default=str))

        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()