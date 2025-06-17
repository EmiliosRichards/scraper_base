import asyncio
import logging
import os
import time
from pprint import pprint

from src.config import ScraperConfig
from src.scraper import scrape_website

# Setup basic logging for the test script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """
    Main function to run the scraper test.
    Initializes config, sets up test parameters, and calls the scraper.
    """
    logger.info("--- Starting Standalone Scraper Test ---")

    # 1. Initialize the dedicated ScraperConfig
    try:
        config = ScraperConfig()
        logger.info("ScraperConfig initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize ScraperConfig: {e}")
        return

    # 2. Define test parameters
    test_url = "https://www.gov.uk/"  # A reliable and complex website for testing
    test_company_name = "UKGovernmentTest"
    
    # Create a unique output directory for this test run
    run_id = time.strftime("%Y%m%d_%H%M%S")
    test_output_dir = os.path.join(config.output_base_dir, f"test_run_{run_id}")
    
    logger.info(f"Test URL: {test_url}")
    logger.info(f"Test Company Name: {test_company_name}")
    logger.info(f"Output Directory: {test_output_dir}")

    # 3. Call the refactored scrape_website function
    try:
        logger.info("Calling scrape_website...")
        scraped_data = await scrape_website(
            given_url=test_url,
            config=config,
            output_dir_for_run=test_output_dir,
            company_name_or_id=test_company_name,
            input_row_id="test_001"
        )
        logger.info("scrape_website call finished.")

        # 4. Print the results in a readable format
        print("\n--- SCRAPER TEST RESULTS ---")
        if scraped_data:
            logger.info(f"Successfully scraped {len(scraped_data)} page(s).")
            print("Scraped Data Overview:")
            # Using pprint for better readability of the list of dicts
            pprint(scraped_data)
            
            # Verify that content files were created
            for item in scraped_data:
                if item.get("content_file_path") and os.path.exists(item["content_file_path"]):
                    logger.info(f"Verified: Content file exists at {item['content_file_path']}")
                else:
                    logger.warning(f"Warning: Content file missing for URL {item.get('url')}")
        else:
            logger.warning("No data was scraped. The function returned an empty list.")
        
        print("--------------------------\n")

    except Exception as e:
        logger.error(f"An error occurred during the scrape_website call: {e}", exc_info=True)

if __name__ == "__main__":
    # Ensure .env is loaded if it exists in the project root
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        from dotenv import load_dotenv
        logger.info(f"Loading .env file from: {dotenv_path}")
        load_dotenv(dotenv_path)
        
    asyncio.run(main())