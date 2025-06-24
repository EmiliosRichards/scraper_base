import logging
import time
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from .config import ScraperConfig

logger = logging.getLogger(__name__)

class InteractionHandler:
    def __init__(self, page: Page, config: ScraperConfig):
        self.page = page
        self.config = config

    async def handle_interactions(self):
        """
        Repeatedly scans for and closes modal dialogs, cookie banners, etc.,
        based on configured selectors and text queries.
        """
        if not self.config.interaction_handler_enabled:
            logger.debug("Interaction handler is disabled in the configuration.")
            return

        start_time = time.time()
        timeout = self.config.interaction_handler_timeout_seconds
        
        while time.time() - start_time < timeout:
            handled_in_pass = False
            
            # Combine selectors and text queries for a single pass
            interactions = [("selector", s) for s in self.config.interaction_selectors] + \
                           [("text", t) for t in self.config.interaction_text_queries]

            for type, query in interactions:
                try:
                    element = None
                    if type == "selector":
                        element = self.page.locator(query).first
                    else: # text
                        element = self.page.locator(f"*:visible:text-is('{query}')").first
                    
                    if await element.is_visible(timeout=2000):
                        logger.info(f"Found and clicking element by {type}: '{query}'")
                        await element.click(timeout=1000)
                        handled_in_pass = True
                        # Once an interaction is handled, restart the scan
                        await self.page.wait_for_timeout(500) # wait for UI to settle
                        break # break from the for loop
                except PlaywrightTimeoutError:
                    # This is expected if the element is not visible
                    logger.debug(f"Element not visible or timed out for {type} '{query}'.")
                except Exception as e:
                    logger.warning(f"Error handling {type} '{query}': {e}")
            
            if handled_in_pass:
                continue # Restart the while-loop to scan again
            else:
                # If a full pass completes with no interactions handled, we can exit.
                logger.debug("No more interactive elements found in a full pass. Exiting handler.")
                return

        logger.warning(f"Interaction handler timed out after {timeout} seconds.")