import os
import sys
import time
import schedule
from datetime import datetime
import logging

sys.path.append('/app/shared')
from queue_client import QueueClient
from models import ScrapedData, InfolegNorma
from infoleg_client import InfolegClient, InfolegConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_year_range(start_year: int, end_year: int, max_normas_per_run: int = 100):
    """Scrape normas from a year range, limiting the number per run"""
    logger.info(f"Starting scraping job for years {start_year}-{end_year}")
    
    queue_client = QueueClient()
    infoleg_client = InfolegClient(InfolegConfig(
        rate_limit_delay=1.5,  # Be respectful to the API
        max_retries=3,
        timeout=30
    ))
    
    normas_processed = 0
    
    for year in range(start_year, end_year + 1):
        if normas_processed >= max_normas_per_run:
            logger.info(f"Reached maximum normas per run ({max_normas_per_run}), stopping")
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
                        "has_full_text": bool(norma.texto_norma)
                    },
                    timestamp=datetime.now().isoformat()
                )
                
                # Send to queue - use to_dict() which handles date serialization
                success = queue_client.send_message('processing', scraped_data.to_dict())
                if success:
                    logger.info(f"Successfully sent norma {norma_id} ({norma.tipo_norma} - {norma.titulo_sumario[:50]}...)")
                    normas_processed += 1
                else:
                    logger.error(f"Failed to send norma {norma_id}")
                
                # Small delay between detailed requests
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error scraping year {year}: {e}")
            continue
    
    logger.info(f"Completed scraping job. Processed {normas_processed} normas")

def scrape_and_send():
    """Main scraping function - scrapes recent years incrementally"""
    
    # ========================================
    # FOR TESTING!!! - HARDCODED VALUES
    # ========================================
    # Test with year 2000, limit to 10 normas for testing
    logger.info("Running test scraping: Year 2000, max 10 normas")
    scrape_year_range(2000, 2000, max_normas_per_run=10)
    
    # ========================================
    # PRODUCTION CODE - COMMENTED OUT FOR TESTING
    # ========================================
    # current_year = datetime.now().year
    # 
    # # For testing, scrape a small range of recent years
    # # In production, you might want to track progress and scrape systematically
    # start_year = max(2020, current_year - 3)  # Last 3 years
    # end_year = current_year
    # 
    # scrape_year_range(start_year, end_year, max_normas_per_run=50)

def main():
    logger.info("InfoLeg Scraper MS started")
    
    # Get configuration from environment
    scrape_mode = os.getenv('SCRAPE_MODE', 'scheduled')  # 'once' or 'scheduled'
    
    if scrape_mode == 'once':
        logger.info("Running in 'once' mode - scraping and exiting")
        scrape_and_send()
        return
    
    # Schedule scraping job
    interval = os.getenv('SCRAPE_INTERVAL_HOURS', '24')
    try:
        interval_hours = int(interval)
        schedule.every(interval_hours).hours.do(scrape_and_send)
        logger.info(f"Scheduled scraping every {interval_hours} hours")
    except ValueError:
        logger.warning(f"Invalid SCRAPE_INTERVAL_HOURS: {interval}, using default 24 hours")
        schedule.every(24).hours.do(scrape_and_send)
    
    # Run once immediately for testing
    scrape_and_send()
    
    # Keep running scheduled jobs
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()