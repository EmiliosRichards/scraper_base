import asyncio
import os
import re
import logging
import time
import heapq
import hashlib # Added for hashing long filenames
import random
from . import caching
from urllib.parse import urljoin, urlparse, urldefrag, urlunparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from bs4.element import Tag # Added for type checking
import httpx # For asynchronous robots.txt checking
from urllib.robotparser import RobotFileParser
from typing import Set, Tuple, Optional, List, Dict, Any
from .config import ScraperConfig
from .utils import normalize_url, get_safe_filename, extract_text_from_html, find_internal_links, _classify_page_type, validate_link_status, process_input_url
from .page_handler import fetch_page_content
from .proxy_manager import ProxyManager

logger = logging.getLogger(__name__)


async def is_allowed_by_robots(url: str, client: httpx.AsyncClient, config: ScraperConfig, input_row_id: Any, company_name_or_id: str) -> bool:
    if not config.respect_robots_txt:
        logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] robots.txt check is disabled.")
        return True
    parsed_url = urlparse(url)
    if parsed_url.scheme == 'file':
        logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Skipping robots.txt check for local file URL: {url}")
        return True
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Fetching robots.txt from: {robots_url}")
        response = await client.get(robots_url, timeout=10, headers={'User-Agent': config.robots_txt_user_agent})
        if response.status_code == 200:
            logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Successfully fetched robots.txt for {url}, status: {response.status_code}")
            rp.parse(response.text.splitlines())
        elif response.status_code == 404:
            logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] robots.txt not found at {robots_url} (status 404), assuming allowed.")
            return True
        else:
            logger.warning(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Failed to fetch robots.txt from {robots_url}, status: {response.status_code}. Assuming allowed.")
            return True
    except httpx.RequestError as e:
        logger.warning(f"[RowID: {input_row_id}, Company: {company_name_or_id}] httpx.RequestError fetching robots.txt from {robots_url}: {e}. Assuming allowed.")
        return True
    except Exception as e:
        logger.error(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Unexpected error processing robots.txt for {robots_url}: {e}. Assuming allowed.", exc_info=True)
        return True
    allowed = rp.can_fetch(config.robots_txt_user_agent, url)
    if not allowed:
        logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Scraping disallowed by robots.txt for URL: {url} (User-agent: {config.robots_txt_user_agent})")
    else:
        logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Scraping allowed by robots.txt for URL: {url}")
    return allowed



async def _perform_scrape_for_entry_point(
    entry_url_to_process: str,
    playwright_context,
    http_client: httpx.AsyncClient,
    config: ScraperConfig,
    output_dir_for_run: str,
    company_name_or_id: str,
    globally_processed_urls: Set[str],
    input_row_id: Any,
    proxy_manager: Optional[ProxyManager],
    proxy_to_use: Optional[str]
) -> Tuple[List[Dict[str, Any]], str, Optional[str], str]:
    """
    Core scraping logic for a single entry point URL.
    Returns page details, status, canonical URL, and collected text for summary.
    """
    final_canonical_entry_url_for_this_attempt: Optional[str] = None
    pages_scraped_this_entry_count = 0
    high_priority_pages_scraped_after_limit_entry = 0
    
    base_scraped_content_dir = os.path.join(output_dir_for_run, config.scraped_content_subdir)
    os.makedirs(base_scraped_content_dir, exist_ok=True)

    company_safe_name = get_safe_filename(
        company_name_or_id,
        config,
        for_url=False,
        max_len=config.filename_company_name_max_len
    )
    
    scraped_page_results: List[Dict[str, Any]] = []
    collected_texts_for_summary: List[str] = []
    priority_pages_collected_count = 0
    priority_page_types_for_summary = {"homepage", "about", "product_service"}

    urls_to_scrape_q: List[Tuple[int, int, str]] = [(-100, 0, entry_url_to_process)]
    heapq.heapify(urls_to_scrape_q)
    processed_urls_this_entry_call: Set[str] = {entry_url_to_process}

    page = await playwright_context.new_page()
    page.set_default_timeout(config.default_page_timeout)
    
    entry_point_status_code: Optional[int] = None

    try:
        while urls_to_scrape_q:
            neg_score, current_depth, current_url_from_queue = heapq.heappop(urls_to_scrape_q)
            current_score = -neg_score
            
            logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Dequeuing URL: '{current_url_from_queue}' (Depth: {current_depth}, Score: {current_score})")

            if config.scraper_max_pages_per_domain > 0 and pages_scraped_this_entry_count >= config.scraper_max_pages_per_domain:
                if current_score < config.scraper_score_threshold_for_limit_bypass or high_priority_pages_scraped_after_limit_entry >= config.scraper_max_high_priority_pages_after_limit:
                    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Page limit reached, skipping '{current_url_from_queue}'.")
                    continue
                else:
                    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Page limit reached, but processing high-priority '{current_url_from_queue}'.")

            html_content, status_code_fetch = await fetch_page_content(page, current_url_from_queue, config, input_row_id, company_name_or_id)
            
            if current_url_from_queue == entry_url_to_process:
                entry_point_status_code = status_code_fetch

            if html_content:
                pages_scraped_this_entry_count += 1
                if pages_scraped_this_entry_count > config.scraper_max_pages_per_domain and current_score >= config.scraper_score_threshold_for_limit_bypass:
                    high_priority_pages_scraped_after_limit_entry += 1

                final_landed_url_normalized = normalize_url(page.url)
                logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Fetched '{current_url_from_queue}', Landed at '{final_landed_url_normalized}', Status: {status_code_fetch}")

                if not final_canonical_entry_url_for_this_attempt and current_depth == 0:
                    final_canonical_entry_url_for_this_attempt = final_landed_url_normalized
                    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Canonical URL for entry '{entry_url_to_process}' set to: '{final_canonical_entry_url_for_this_attempt}'")
                
                if final_landed_url_normalized in globally_processed_urls:
                    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] URL '{final_landed_url_normalized}' already globally processed. Skipping.")
                    continue
                
                globally_processed_urls.add(final_landed_url_normalized)
                processed_urls_this_entry_call.add(final_landed_url_normalized)

                cleaned_text = extract_text_from_html(html_content)
                
                landed_url_safe_name = get_safe_filename(final_landed_url_normalized, config, for_url=True)
                content_filename = f"{company_safe_name}__{landed_url_safe_name}.txt"
                content_filepath = os.path.join(base_scraped_content_dir, content_filename)
                
                try:
                    with open(content_filepath, 'w', encoding='utf-8') as f:
                        f.write(cleaned_text)
                    
                    page_type = _classify_page_type(final_landed_url_normalized, config)
                    
                    page_result = {
                        "url": final_landed_url_normalized,
                        "status": status_code_fetch,
                        "content_file_path": content_filepath,
                        "page_type": page_type,
                        "summary_text": None
                    }
                    scraped_page_results.append(page_result)

                    if page_type in priority_page_types_for_summary and priority_pages_collected_count < config.scraper_pages_for_summary_count:
                        collected_texts_for_summary.append(cleaned_text)
                        priority_pages_collected_count += 1
                        logger.debug(f"[RowID: {input_row_id}] Collected text from '{final_landed_url_normalized}' for summary.")

                except IOError as e:
                    logger.error(f"[RowID: {input_row_id}] IOError saving content for '{final_landed_url_normalized}': {e}")

                if current_depth < config.max_depth_internal_links:
                    newly_found_links = find_internal_links(html_content, final_landed_url_normalized, config, input_row_id, company_name_or_id)
                    for link_url, link_score in newly_found_links:
                        if link_url not in globally_processed_urls and link_url not in processed_urls_this_entry_call:
                            heapq.heappush(urls_to_scrape_q, (-link_score, current_depth + 1, link_url))
                            processed_urls_this_entry_call.add(link_url)
            else:
                logger.warning(f"[RowID: {input_row_id}] Failed to fetch content from '{current_url_from_queue}'. Status: {status_code_fetch}.")
                
                # Report proxy failure if applicable
                if proxy_manager and proxy_to_use and status_code_fetch in [-1, -3]: # Timeout or Connection Refused
                    proxy_manager.report_failure(proxy_to_use)

                if current_url_from_queue == entry_url_to_process:
                    status_map = {-1: "TimeoutError", -2: "DNSError", -3: "ConnectionRefused", -4: "PlaywrightError", -5: "GenericScrapeError", -6: "RequestAborted", -7: "CaptchaFailed"}
                    if status_code_fetch is None:
                        http_status_report = "UnknownScrapeError"
                    else:
                        http_status_report = f"HTTPError_{status_code_fetch}" if status_code_fetch > 0 else status_map.get(status_code_fetch, "UnknownScrapeError")
                    logger.error(f"[RowID: {input_row_id}] Critical failure on entry point '{entry_url_to_process}'. Status: {http_status_report}.")
                    await page.close()
                    return [], http_status_report, None, ""
        
        await page.close()

        final_summary_input_text = ""
        if collected_texts_for_summary:
            final_summary_input_text = " ".join(collected_texts_for_summary)
            if len(final_summary_input_text) > config.llm_max_input_chars_for_summary:
                final_summary_input_text = final_summary_input_text[:config.llm_max_input_chars_for_summary]
                logger.info(f"[RowID: {input_row_id}] Truncated summary text to {config.llm_max_input_chars_for_summary} chars.")

        if scraped_page_results:
            scraped_page_results[0]["summary_text"] = final_summary_input_text
            logger.info(f"[RowID: {input_row_id}] Successfully scraped {len(scraped_page_results)} pages for entry '{entry_url_to_process}'.")
            return scraped_page_results, "Success", final_canonical_entry_url_for_this_attempt, final_summary_input_text
        else:
            status_map = {-1: "TimeoutError", -2: "DNSError", -3: "ConnectionRefused", -4: "PlaywrightError", -5: "GenericScrapeError", -6: "RequestAborted", -7: "CaptchaFailed"}
            if entry_point_status_code is None:
                final_status = "NoContentScraped_Overall"
            else:
                final_status = f"HTTPError_{entry_point_status_code}" if entry_point_status_code > 0 else status_map.get(entry_point_status_code, "NoContentScraped_Overall")
            logger.warning(f"[RowID: {input_row_id}] No content scraped for entry '{entry_url_to_process}'. Final status: {final_status}")
            return [], final_status, final_canonical_entry_url_for_this_attempt, ""
            
    except Exception as e:
        logger.error(f"[RowID: {input_row_id}] General error during scraping for '{entry_url_to_process}': {e}", exc_info=True)
        if not page.is_closed(): await page.close()
        return [], f"GeneralScrapingError_{type(e).__name__}", final_canonical_entry_url_for_this_attempt, ""


async def scrape_website(
    given_url: str,
    config: ScraperConfig,
    output_dir_for_run: str,
    company_name_or_id: str,
    input_row_id: Any = "N/A"
) -> List[Dict[str, Any]]:
    """
    Performs a comprehensive scrape of a website based on a given URL and configuration.
    Includes caching to avoid re-scraping the same content.
    """
    log_identifier = f"[RowID: {input_row_id}, Company: {company_name_or_id}]"
    logger.info(f"{log_identifier} Starting scrape for URL: {given_url}")

    # --- Caching Logic: Check before scraping ---
    if config.caching_enabled:
        cache_key = caching.generate_cache_key(given_url)
        cached_results = caching.load_from_cache(cache_key, config.cache_dir)
        if cached_results is not None:
            logger.info(f"{log_identifier} Scrape data for '{given_url}' loaded from cache.")
            return cached_results

    processed_url, status = process_input_url(given_url, config.url_probing_tlds, log_identifier)

    if not processed_url:
        logger.warning(f"{log_identifier} The URL '{given_url}' was determined to be invalid. Aborting scrape.")
        return []

    normalized_given_url = processed_url
    globally_processed_urls: Set[str] = set()

    async with httpx.AsyncClient(follow_redirects=True, verify=False) as http_client:
        if not await is_allowed_by_robots(normalized_given_url, http_client, config, input_row_id, company_name_or_id):
            return [{"url": normalized_given_url, "status": "RobotsDisallowed", "content_file_path": None, "page_type": "unknown", "summary_text": None}]
    
    os.makedirs(output_dir_for_run, exist_ok=True)

    results = []
    async with async_playwright() as p:
        browser = None
        try:
            launch_options: Dict[str, Any] = {'headless': config.headless_mode}
            proxy_manager = None
            proxy_to_use = None

            if config.proxy_enabled:
                proxy_manager = ProxyManager(config)
                proxy_to_use = proxy_manager.get_proxy()
                if proxy_to_use:
                    logger.info(f"{log_identifier} Using proxy: {proxy_to_use}")
                    launch_options['proxy'] = {'server': proxy_to_use}
                else:
                    logger.warning(f"{log_identifier} Proxy is enabled, but no healthy proxy could be obtained. Proceeding without proxy.")

            browser = await p.chromium.launch(**launch_options)
            user_agent = random.choice(config.user_agents) if config.user_agents else config.user_agent

            context = await browser.new_context(
                user_agent=user_agent,
                java_script_enabled=True,
                ignore_https_errors=True,
                extra_http_headers=config.default_headers
            )
            
            logger.info(f"{log_identifier} Attempting scrape with entry point: {normalized_given_url}")
            async with httpx.AsyncClient(follow_redirects=True, verify=False) as validation_client:
                results, status, _, _ = await _perform_scrape_for_entry_point(
                    normalized_given_url, context, validation_client, config, output_dir_for_run,
                    company_name_or_id, globally_processed_urls, input_row_id,
                    proxy_manager, proxy_to_use
                )
            
            logger.info(f"{log_identifier} Scrape attempt for '{normalized_given_url}' finished with status: {status}. Returning results.")
            
        except Exception as e:
            logger.error(f"{log_identifier} Outer error in scrape_website for '{given_url}': {e}", exc_info=True)
        finally:
            if browser: await browser.close()

    # --- Caching Logic: Save after scraping ---
    if config.caching_enabled and results:
        cache_key = caching.generate_cache_key(given_url)
        caching.save_to_cache(cache_key, results, config.cache_dir)

    return results