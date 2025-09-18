import os
import sys
import logging
from datetime import datetime
from flask import Flask, request, jsonify

sys.path.append('/app/00-shared')
from scraper_service import ScraperService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize scraper service
scraper_service = ScraperService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'enhanced-scraper-ms',
        'version': '2.0',
        'features': ['s3_cache', 'range_scraping', 'force_processing'],
        'timestamp': datetime.now().isoformat()
    })


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    """Enhanced endpoint to scrape norm(s) by ID or range with caching support"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Missing request body',
                'examples': {
                    'single_id': {'infoleg_id': 183532, 'force': False},
                    'range': {'start_id': 183530, 'end_id': 183535, 'force': False},
                    'force_scrape': {'infoleg_id': 183532, 'force': True}
                }
            }), 400

        # Get parameters
        infoleg_id = data.get('infoleg_id')
        start_id = data.get('start_id')
        end_id = data.get('end_id')
        force = data.get('force', False)
        max_docs = data.get('max_docs', 10)  # Limit for range operations

        # Validate input
        if infoleg_id and (start_id or end_id):
            return jsonify({
                'error': 'Cannot specify both infoleg_id and range (start_id/end_id)'
            }), 400

        if not infoleg_id and not (start_id and end_id):
            return jsonify({
                'error': 'Must specify either infoleg_id or both start_id and end_id'
            }), 400

        # Single ID scraping
        if infoleg_id:
            if not isinstance(infoleg_id, int) or infoleg_id <= 0:
                return jsonify({
                    'error': 'infoleg_id must be a positive integer'
                }), 400

            logger.info(f"Received scrape request for norm ID: {infoleg_id} (force={force})")

            # Check cache first if not forcing
            if not force and scraper_service.is_cached(infoleg_id):
                logger.info(f"Norm {infoleg_id} already cached (use force=true to override)")
                return jsonify({
                    'status': 'cached',
                    'message': f'Norm {infoleg_id} already in cache (use force=true to override)',
                    'infoleg_id': infoleg_id,
                    'cached': True,
                    'timestamp': datetime.now().isoformat()
                })

            # Scrape the norm
            success, source = scraper_service.scrape_specific_norma(infoleg_id, force=force)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Successfully scraped and queued norm {infoleg_id}',
                    'infoleg_id': infoleg_id,
                    'source': source,
                    'forced': force,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to scrape norm {infoleg_id}',
                    'infoleg_id': infoleg_id,
                    'reason': source,
                    'forced': force
                }), 500

        # Range scraping
        else:
            if not all(isinstance(x, int) and x > 0 for x in [start_id, end_id]):
                return jsonify({
                    'error': 'start_id and end_id must be positive integers'
                }), 400

            if start_id >= end_id:
                return jsonify({
                    'error': 'start_id must be less than end_id'
                }), 400

            if not isinstance(max_docs, int) or max_docs <= 0 or max_docs > 100:
                return jsonify({
                    'error': 'max_docs must be between 1 and 100'
                }), 400

            logger.info(f"Received range scrape request for IDs {start_id}-{end_id}, max {max_docs} (force={force})")

            # Use scraper service for range scraping
            result = scraper_service.scrape_range(start_id, end_id, max_docs, force)

            return jsonify({
                'status': 'completed',
                'message': 'Range scraping completed',
                'forced': force,
                'timestamp': datetime.now().isoformat(),
                **result
            })

    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/process', methods=['POST'])
def process_endpoint():
    """Endpoint to force scrape and send norm(s) to processing queue"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Missing request body',
                'examples': {
                    'single_id': {'infoleg_id': 183532},
                    'range': {'start_id': 183530, 'end_id': 183535},
                }
            }), 400

        # Get parameters
        infoleg_id = data.get('infoleg_id')
        start_id = data.get('start_id')
        end_id = data.get('end_id')
        max_docs = data.get('max_docs', 10)  # Limit for range operations

        # Validate input
        if infoleg_id and (start_id or end_id):
            return jsonify({
                'error': 'Cannot specify both infoleg_id and range (start_id/end_id)'
            }), 400

        if not infoleg_id and not (start_id and end_id):
            return jsonify({
                'error': 'Must specify either infoleg_id or both start_id and end_id'
            }), 400

        # Single ID processing
        if infoleg_id:
            if not isinstance(infoleg_id, int) or infoleg_id <= 0:
                return jsonify({
                    'error': 'infoleg_id must be a positive integer'
                }), 400

            logger.info(f"Received process request for norm ID: {infoleg_id} (force=True)")

            # Force scrape and send to processing queue
            success, source = scraper_service.scrape_specific_norma(infoleg_id, force=True)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Successfully processed norm {infoleg_id}',
                    'infoleg_id': infoleg_id,
                    'source': source,
                    'forced': True,
                    'action': 'process',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to process norm {infoleg_id}',
                    'infoleg_id': infoleg_id,
                    'reason': source,
                    'action': 'process'
                }), 500

        # Range processing
        else:
            if not all(isinstance(x, int) and x > 0 for x in [start_id, end_id]):
                return jsonify({
                    'error': 'start_id and end_id must be positive integers'
                }), 400

            if start_id >= end_id:
                return jsonify({
                    'error': 'start_id must be less than end_id'
                }), 400

            if not isinstance(max_docs, int) or max_docs <= 0 or max_docs > 100:
                return jsonify({
                    'error': 'max_docs must be between 1 and 100'
                }), 400

            logger.info(f"Received range process request for IDs {start_id}-{end_id}, max {max_docs} (force=True)")

            # Use scraper service for range processing
            result = scraper_service.process_range(start_id, end_id, max_docs)

            return jsonify({
                'status': 'completed',
                'message': 'Range processing completed',
                'forced': True,
                'action': 'process',
                'timestamp': datetime.now().isoformat(),
                **result
            })

    except Exception as e:
        logger.error(f"Error in process endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'action': 'process'
        }), 500


@app.route('/cache/stats', methods=['GET'])
def cache_stats_endpoint():
    """Endpoint to get cache statistics"""
    try:
        stats = scraper_service.get_cache_stats()
        return jsonify({
            'status': 'success',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/cache/list', methods=['GET'])
def cache_list_endpoint():
    """Endpoint to list cached norms"""
    try:
        limit = request.args.get('limit', 100, type=int)
        if limit > 1000:
            limit = 1000

        cached_norms = scraper_service.list_cached_normas(limit=limit)

        return jsonify({
            'status': 'success',
            'cached_norms': cached_norms,
            'count': len(cached_norms),
            'limit': limit,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error listing cached norms: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def main():
    """Main entry point"""
    logger.info("InfoLeg Enhanced Scraper API started")

    port = int(os.getenv('SCRAPER_PORT', 8003))
    debug_mode = os.getenv('DEBUG') == '1'

    logger.info(f"Starting scraper API service on port {port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)


if __name__ == "__main__":
    main()