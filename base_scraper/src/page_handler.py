import logging
from typing import Optional, Tuple, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .config import ScraperConfig
from .interaction_handler import InteractionHandler
from .captcha_solver import get_captcha_solver

logger = logging.getLogger(__name__)

async def fetch_page_content(page: Page, url: str, config: ScraperConfig, input_row_id: Any, company_name_or_id: str) -> Tuple[Optional[str], Optional[int]]:
    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Navigating to URL: {url}")
    try:
        response = await page.goto(url, timeout=config.default_navigation_timeout, wait_until='domcontentloaded')
        if response:
            logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Navigation to {url} successful. Status: {response.status}")
            if response.ok:
                # --- Pre-Scrape Checks ---
                # 1. Handle interactions (cookie banners, etc.)
                interaction_handler = InteractionHandler(page, config)
                await interaction_handler.handle_interactions()

                # 2. Handle CAPTCHAs
                captcha_solver = get_captcha_solver(page, config)
                if captcha_solver:
                    if await captcha_solver.detect_captcha():
                        logger.info(f"[RowID: {input_row_id}] CAPTCHA detected on {url}. Invoking solver.")
                        solved = await captcha_solver.solve_captcha()
                        if not solved:
                            logger.error(f"[RowID: {input_row_id}] CAPTCHA solver failed for {url}. Aborting page scrape.")
                            return None, -7 # Custom status code for CAPTCHA failure
                
                # --- Proceed with scraping ---
                if config.scraper_networkidle_timeout_ms > 0:
                    logger.debug(f"[RowID: {input_row_id}] Waiting for networkidle on {url} (timeout: {config.scraper_networkidle_timeout_ms}ms)...")
                    try:
                        await page.wait_for_load_state('networkidle', timeout=config.scraper_networkidle_timeout_ms)
                        logger.debug(f"[RowID: {input_row_id}] Networkidle achieved for {url}.")
                    except PlaywrightTimeoutError:
                        logger.info(f"[RowID: {input_row_id}] Timeout waiting for networkidle on {url}. Proceeding.")
                
                content = await page.content()
                logger.debug(f"[RowID: {input_row_id}] Content fetched successfully for {url}.")
                return content, response.status
            else:
                logger.warning(f"[RowID: {input_row_id}] HTTP error for {url}: Status {response.status}. No content fetched.")
                return None, response.status
        else:
            logger.error(f"[RowID: {input_row_id}] Failed to get a response object for {url}.")
            return None, None
    except PlaywrightTimeoutError as e:
        error_message = str(e)
        logger.error(f"[RowID: {input_row_id}] Playwright navigation timeout for {url}: {error_message}")
        if "net::ERR_NAME_NOT_RESOLVED" in error_message: return None, -2
        return None, -1
    except PlaywrightError as e:
        error_message = str(e)
        logger.error(f"[RowID: {input_row_id}] Playwright error during navigation to {url}: {error_message}")
        if "net::ERR_NAME_NOT_RESOLVED" in error_message: return None, -2
        elif "net::ERR_CONNECTION_REFUSED" in error_message: return None, -3
        elif "net::ERR_ABORTED" in error_message: return None, -6
        return None, -4
    except Exception as e:
        logger.error(f"[RowID: {input_row_id}] Unexpected error fetching page {url}: {e}", exc_info=True)
        return None, -5