import os
import sys
import time
import schedule
from datetime import datetime
import logging
from flask import Flask, request, jsonify
import threading

sys.path.append('/app/00-shared')
from queue_client import QueueClient
from models import ScrapedData, InfolegNorma
from infoleg_client import InfolegClient, InfolegConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize startup logic when imported (for gunicorn)
def initialize_app():
    """Initialize the app for gunicorn"""
    logger.info("InfoLeg Scraper MS started")
    
    # Get configuration from environment
    scrape_mode = os.getenv('SCRAPE_MODE', 'service')  # 'once', 'scheduled', or 'service'
    
    if scrape_mode == 'scheduled':
        # Schedule scraping job
        interval = os.getenv('SCRAPE_INTERVAL_HOURS', '24')
        try:
            interval_hours = int(interval)
            schedule.every(interval_hours).hours.do(scrape_and_send)
            logger.info(f"Scheduled scraping every {interval_hours} hours")
        except ValueError:
            logger.warning(
                f"Invalid SCRAPE_INTERVAL_HOURS: {interval}, using default 24 hours"
            )
            schedule.every(24).hours.do(scrape_and_send)

        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Started scheduled mode with background scheduler")
    else:
        logger.info(f"Running in '{scrape_mode}' mode - API service")

# Initialize when imported (for gunicorn)
initialize_app()


def scrape_year_range(start_year: int, end_year: int, max_normas_per_run: int = 100):
    """Scrape normas from a year range, limiting the number per run"""
    logger.info(f"Starting scraping job for years {start_year}-{end_year}")

    queue_client = QueueClient()
    infoleg_client = InfolegClient(
        InfolegConfig(
            rate_limit_delay=1.5, max_retries=3, timeout=30  # Be respectful to the API
        )
    )

    normas_processed = 0

    for year in range(start_year, end_year + 1):
        if normas_processed >= max_normas_per_run:
            logger.info(
                f"Reached maximum normas per run ({max_normas_per_run}), stopping"
            )
            break

        logger.info(f"Scraping normas for year {year}")

        try:
            for norma_summary in infoleg_client.get_normas_by_year(year, limit=20):
                if normas_processed >= max_normas_per_run:
                    break

                norma_id = norma_summary.get('id')
                if not norma_id:
                    continue

                # Get detailed information for this norma
                detailed_norma = infoleg_client.get_norma_details(norma_id)
                if not detailed_norma:
                    logger.warning(f"Could not retrieve details for norma {norma_id}")
                    continue

                # Parse the response
                parsed_norma = infoleg_client.parse_norma_response(detailed_norma)

                # Create InfolegNorma object
                norma = InfolegNorma(**parsed_norma)

                # Create ScrapedData
                scraped_data = ScrapedData(
                    norma=norma,
                    api_url=f"https://servicios.infoleg.gob.ar/infolegInternet/api/v2.0/nacionales/normativos?id={norma_id}",
                    metadata={
                        "scraper_version": "1.0",
                        "scraped_year": year,
                        "api_source": "infoleg.gob.ar",
                        "has_full_text": bool(norma.texto_norma),
                    },
                    timestamp=datetime.now().isoformat(),
                )

                # Send to queue - use to_dict() which handles date serialization
                success = queue_client.send_message(
                    'processing', scraped_data.to_dict()
                )
                if success:
                    logger.info(
                        f"Successfully sent norma {norma_id} ({norma.tipo_norma} - {norma.titulo_sumario[:50]}...)"
                    )
                    normas_processed += 1
                else:
                    logger.error(f"Failed to send norma {norma_id}")

                # Small delay between detailed requests
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error scraping year {year}: {e}")
            continue

    logger.info(f"Completed scraping job. Processed {normas_processed} normas")


def scrape_specific_norma(norma_id: int):
    """Scrape a specific norma by its infoleg_id"""
    logger.info(f"Scraping specific norma with ID: {norma_id}")

    queue_client = QueueClient()
    infoleg_client = InfolegClient(
        InfolegConfig(
            rate_limit_delay=1.5, max_retries=3, timeout=30  # Be respectful to the API
        )
    )

    try:
        # Get detailed information for this specific norma
        detailed_norma = infoleg_client.get_norma_details(norma_id)
        if not detailed_norma:
            logger.error(f"Could not retrieve details for norma {norma_id}")
            return False

        # Parse the response
        parsed_norma = infoleg_client.parse_norma_response(detailed_norma)

        # Create InfolegNorma object
        norma = InfolegNorma(**parsed_norma)

        # Create ScrapedData
        scraped_data = ScrapedData(
            norma=norma,
            api_url=f"https://servicios.infoleg.gob.ar/infolegInternet/api/v2.0/nacionales/normativos?id={norma_id}",
            metadata={
                "scraper_version": "1.1",
                "scrape_mode": "specific_target",
                "api_source": "infoleg.gob.ar",
                "has_full_text": bool(norma.texto_norma),
                "has_updated_text": bool(norma.texto_norma_actualizado),
            },
            timestamp=datetime.now().isoformat(),
        )

        # Send to queue - use to_dict() which handles date serialization
        success = queue_client.send_message('processing', scraped_data.to_dict())
        if success:
            logger.info(
                f"Successfully sent norma {norma_id} ({norma.tipo_norma} - {norma.titulo_sumario[:50]}...)"
            )
            logger.info(
                f"Norma details: Sancion date: {norma.sancion}, Has original text: {bool(norma.texto_norma)}, Has updated text: {bool(norma.texto_norma_actualizado)}"
            )
            return True
        else:
            logger.error(f"Failed to send norma {norma_id}")
            return False

    except Exception as e:
        logger.error(f"Error scraping norma {norma_id}: {e}")
        return False


def scrape_and_send():
    """Main scraping function - targeting specific norma for testing"""

    # ========================================
    # TARGET SPECIFIC NORMA FOR TESTING
    # ========================================
    target_norma_id = 183532
    logger.info(f"Running targeted scraping for norma ID: {target_norma_id}")

    success = scrape_specific_norma(target_norma_id)
    if success:
        logger.info(f"Successfully scraped and sent norma {target_norma_id}")
    else:
        logger.error(f"Failed to scrape norma {target_norma_id}")

    # ========================================
    # COMMENTED OUT: YEAR RANGE SCRAPING
    # ========================================
    # scrape_year_range(2000, 2000, max_normas_per_run=10)


# Flask API endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'scraper-ms',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    """Endpoint to scrape a specific norma by ID"""
    try:
        data = request.get_json()
        if not data or 'infoleg_id' not in data:
            return jsonify({
                'error': 'Missing infoleg_id in request body',
                'example': {'infoleg_id': 183532}
            }), 400

        infoleg_id = data['infoleg_id']
        if not isinstance(infoleg_id, int) or infoleg_id <= 0:
            return jsonify({
                'error': 'infoleg_id must be a positive integer'
            }), 400

        logger.info(f"Received scrape request for norma ID: {infoleg_id}")
        
        # Scrape the norma
        success = scrape_specific_norma(infoleg_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Successfully scraped and queued norma {infoleg_id}',
                'infoleg_id': infoleg_id,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to scrape norma {infoleg_id}',
                'infoleg_id': infoleg_id
            }), 500

    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/scrape/batch', methods=['POST'])
def scrape_batch_endpoint():
    """Endpoint to scrape multiple normas by ID range"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Missing request body',
                'example': {'start_id': 183530, 'end_id': 183540, 'max_docs': 10}
            }), 400

        start_id = data.get('start_id')
        end_id = data.get('end_id')
        max_docs = data.get('max_docs', 10)

        if not all(isinstance(x, int) and x > 0 for x in [start_id, end_id]):
            return jsonify({
                'error': 'start_id and end_id must be positive integers'
            }), 400

        if start_id >= end_id:
            return jsonify({
                'error': 'start_id must be less than end_id'
            }), 400

        logger.info(f"Received batch scrape request for IDs {start_id}-{end_id}, max {max_docs}")
        
        scraped_count = 0
        failed_count = 0
        
        for norma_id in range(start_id, min(end_id + 1, start_id + max_docs)):
            try:
                success = scrape_specific_norma(norma_id)
                if success:
                    scraped_count += 1
                else:
                    failed_count += 1
                    
                # Small delay between requests
                time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error scraping norma {norma_id}: {e}")
                failed_count += 1
        
        return jsonify({
            'status': 'completed',
            'message': f'Batch scraping completed',
            'scraped_count': scraped_count,
            'failed_count': failed_count,
            'total_requested': min(max_docs, end_id - start_id + 1),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in batch scrape endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def run_scheduler():
    """Run the background scheduler in a separate thread"""
    logger.info("Background scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def main():
    logger.info("InfoLeg Scraper MS started")

    # Get configuration from environment
    scrape_mode = os.getenv('SCRAPE_MODE', 'service')  # 'once', 'scheduled', or 'service'
    port = int(os.getenv('SCRAPER_PORT', 8003))
    debug_mode = os.getenv('DEBUG', '0') == '1'

    if scrape_mode == 'once':
        logger.info("Running in 'once' mode - scraping and exiting")
        scrape_and_send()
        return
    elif scrape_mode == 'scheduled':
        # Schedule scraping job
        interval = os.getenv('SCRAPE_INTERVAL_HOURS', '24')
        try:
            interval_hours = int(interval)
            schedule.every(interval_hours).hours.do(scrape_and_send)
            logger.info(f"Scheduled scraping every {interval_hours} hours")
        except ValueError:
            logger.warning(
                f"Invalid SCRAPE_INTERVAL_HOURS: {interval}, using default 24 hours"
            )
            schedule.every(24).hours.do(scrape_and_send)

        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Start Flask API
        logger.info(f"Starting scraper API service on port {port} (debug={debug_mode})")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    else:
        # Default service mode - just run Flask API
        logger.info(f"Running in 'service' mode - API only on port {port} (debug={debug_mode})")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)


if __name__ == "__main__":
    main()
