"""Minimal API for processor service replay functionality"""

import logging
from flask import Flask, request, jsonify
from typing import Dict, Any
import os

from s3_cache import ProcessorS3Cache
from rabbitmq_client import RabbitMQClient

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize cache and queue client
cache = ProcessorS3Cache(
    bucket_name=os.getenv('PROCESSOR_S3_BUCKET', 'processor-cache'),
    endpoint_url=os.getenv('S3_ENDPOINT_URL')
)
queue_client = RabbitMQClient()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "processor",
        "cache_available": cache.s3_client is not None
    })


@app.route('/replay', methods=['POST'])
def replay_cached_document():
    """Replay a cached processed document to the embedding queue"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400

        infoleg_id = data.get('infoleg_id')
        version = data.get('version', 'latest')

        if not infoleg_id:
            return jsonify({
                "status": "error",
                "message": "infoleg_id is required"
            }), 400

        # Get cached processed data
        cached_data = cache.get_cached_processed_data(infoleg_id, version)

        if not cached_data:
            return jsonify({
                "status": "error",
                "message": f"No cached data found for document {infoleg_id} (version: {version})",
                "reason": "cache_miss"
            }), 404

        # Send to embedding queue
        success = queue_client.send_message('embedding', cached_data)

        if success:
            logger.info(f"Replayed cached document {infoleg_id} (version: {version}) to embedding queue")
            return jsonify({
                "status": "success",
                "message": f"Successfully replayed document {infoleg_id} to embedding queue",
                "infoleg_id": infoleg_id,
                "version": version,
                "source": "cache"
            })
        else:
            logger.error(f"Failed to send cached document {infoleg_id} to embedding queue")
            return jsonify({
                "status": "error",
                "message": f"Failed to send document {infoleg_id} to embedding queue",
                "reason": "queue_send_failed"
            }), 500

    except Exception as e:
        logger.error(f"Error in replay endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@app.route('/replay/batch', methods=['POST'])
def replay_batch_documents():
    """Replay multiple cached documents to the embedding queue"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400

        document_specs = data.get('documents', [])

        if not document_specs:
            return jsonify({
                "status": "error",
                "message": "documents array is required"
            }), 400

        results = []
        success_count = 0
        failed_count = 0

        for spec in document_specs:
            infoleg_id = spec.get('infoleg_id')
            version = spec.get('version', 'latest')

            if not infoleg_id:
                results.append({
                    "infoleg_id": None,
                    "status": "error",
                    "message": "infoleg_id is required"
                })
                failed_count += 1
                continue

            # Get cached data
            cached_data = cache.get_cached_processed_data(infoleg_id, version)

            if not cached_data:
                results.append({
                    "infoleg_id": infoleg_id,
                    "version": version,
                    "status": "error",
                    "message": "No cached data found"
                })
                failed_count += 1
                continue

            # Send to queue
            success = queue_client.send_message('embedding', cached_data)

            if success:
                results.append({
                    "infoleg_id": infoleg_id,
                    "version": version,
                    "status": "success",
                    "message": "Replayed to embedding queue"
                })
                success_count += 1
            else:
                results.append({
                    "infoleg_id": infoleg_id,
                    "version": version,
                    "status": "error",
                    "message": "Failed to send to embedding queue"
                })
                failed_count += 1

        logger.info(f"Batch replay completed: {success_count} success, {failed_count} failed")

        return jsonify({
            "status": "completed",
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(document_specs),
            "results": results
        })

    except Exception as e:
        logger.error(f"Error in batch replay endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@app.route('/cache/info/<int:infoleg_id>', methods=['GET'])
def get_cache_info(infoleg_id: int):
    """Get cache information for a specific document"""
    try:
        versions = cache.get_document_versions(infoleg_id)

        if not versions:
            return jsonify({
                "status": "not_cached",
                "infoleg_id": infoleg_id,
                "message": "Document not found in cache"
            }), 404

        # Get metadata
        metadata = cache._get_metadata(infoleg_id)

        return jsonify({
            "status": "cached",
            "infoleg_id": infoleg_id,
            "versions": versions,
            "latest_version": metadata.get("latest_version") if metadata else None,
            "created_at": metadata.get("created_at") if metadata else None,
            "updated_at": metadata.get("updated_at") if metadata else None
        })

    except Exception as e:
        logger.error(f"Error getting cache info for {infoleg_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8004, debug=False)