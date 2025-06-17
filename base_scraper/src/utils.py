import logging
import re
import socket
import hashlib
from urllib.parse import urljoin, urlparse, urldefrag, quote, ParseResult
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import List, Tuple, Optional, Any
import httpx

from .config import ScraperConfig

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """
    Normalizes a URL to a canonical form.
    """
    try:
        url_no_frag, _ = urldefrag(url)
        parsed = urlparse(url_no_frag)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path
        common_indexes = ['index.html', 'index.htm', 'index.php', 'default.html', 'default.htm', 'index.asp', 'default.asp']
        for index_file in common_indexes:
            if path.endswith(f'/{index_file}'):
                path = path[:-len(index_file)]
                break
        if netloc and path and not path.startswith('/'):
            path = '/' + path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        if not path and netloc:
            path = '/'
        query = ''
        if parsed.query:
            params = parsed.query.split('&')
            ignored_params = {'fallback'}
            filtered_params = [p for p in params if (p.split('=')[0].lower() if '=' in p else p.lower()) not in ignored_params]
            if filtered_params:
                query = '&'.join(sorted(filtered_params))
        return urlparse('')._replace(scheme=scheme, netloc=netloc, path=path, params=parsed.params, query=query, fragment='').geturl()
    except Exception as e:
        logger.error(f"Error normalizing URL '{url}': {e}. Returning original URL.", exc_info=True)
        return url

def get_safe_filename(name_or_url: str, config: ScraperConfig, for_url: bool = False, max_len: int = 100) -> str:
    if for_url:
        logger.info(f"get_safe_filename (for_url=True): Input for filename generation='{name_or_url}'")
    original_input = name_or_url
    if for_url:
        parsed_original_url = urlparse(original_input)
        domain_part = re.sub(r'^www\.', '', parsed_original_url.netloc)
        domain_part = re.sub(r'[^\w-]', '', domain_part)[:config.filename_url_domain_max_len]
        url_hash = hashlib.sha256(original_input.encode('utf-8')).hexdigest()[:config.filename_url_hash_max_len]
        safe_name = f"{domain_part}_{url_hash}" # Use the sanitized domain_part
        logger.debug(f"DEBUG PATH: get_safe_filename (for_url=True) output: '{safe_name}' from input '{original_input}'") # DEBUG PATH LENGTH
        return safe_name
    else:
        name_or_url = re.sub(r'^https?://', '', name_or_url)
        safe_name = re.sub(r'[^\w.-]', '_', name_or_url)
        safe_name_truncated = safe_name[:max_len]
        logger.debug(f"DEBUG PATH: get_safe_filename (for_url=False) output: '{safe_name_truncated}' (original sanitized: '{safe_name}', max_len: {max_len}) from input '{original_input}'") # DEBUG PATH LENGTH
        return safe_name_truncated

def extract_text_from_html(html_content: str) -> str:
    if not html_content: return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_internal_links(html_content: str, base_url: str, config: ScraperConfig, input_row_id: Any, company_name_or_id: str) -> List[Tuple[str, int]]:
    if not html_content: return []
    scored_links: List[Tuple[str, int]] = []
    soup = BeautifulSoup(html_content, 'html.parser')
    normalized_base_url_str = normalize_url(base_url)
    parsed_base_url = urlparse(normalized_base_url_str)

    for link_tag in soup.find_all('a', href=True):
        if not isinstance(link_tag, Tag): continue
        href_attr = link_tag.get('href')
        current_href: Optional[str] = None
        if isinstance(href_attr, str): current_href = href_attr.strip()
        elif isinstance(href_attr, list) and href_attr and isinstance(href_attr[0], str): current_href = href_attr[0].strip()
        if not current_href: continue

        absolute_url_raw = urljoin(base_url, current_href)
        normalized_link_url = normalize_url(absolute_url_raw)
        parsed_normalized_link = urlparse(normalized_link_url)

        if parsed_normalized_link.scheme not in ['http', 'https']: continue
        if parsed_normalized_link.netloc != parsed_base_url.netloc: continue

        link_text = link_tag.get_text().lower().strip()
        link_href_lower = normalized_link_url.lower()
        initial_keyword_match = False
        if config.target_link_keywords:
            if any(kw in link_text for kw in config.target_link_keywords) or \
               any(kw in link_href_lower for kw in config.target_link_keywords):
                initial_keyword_match = True
        if not initial_keyword_match: continue

        if config.scraper_exclude_link_path_patterns:
            path_lower = parsed_normalized_link.path.lower()
            if any(p and p in path_lower for p in config.scraper_exclude_link_path_patterns):
                logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Link '{normalized_link_url}' hard excluded by pattern in path: '{path_lower}'.")
                continue
        
        score = 0
        path_segments = [seg for seg in parsed_normalized_link.path.lower().strip('/').split('/') if seg]
        num_segments = len(path_segments)

        # Tier 1: Critical Keywords (Score: 100)
        if config.scraper_critical_priority_keywords and any(kw in path_segments for kw in config.scraper_critical_priority_keywords):
            score = 100
            if num_segments > config.scraper_max_keyword_path_segments:
                score -= min(20, (num_segments - config.scraper_max_keyword_path_segments) * 5)
        
        # Tier 2: High-Priority Keywords (Score: 90)
        if score < 90 and config.scraper_high_priority_keywords and any(kw in path_segments for kw in config.scraper_high_priority_keywords):
            score = 90
            if num_segments > config.scraper_max_keyword_path_segments:
                score -= min(20, (num_segments - config.scraper_max_keyword_path_segments) * 5)

        # Tier 3: Other Target Keywords as exact path segments (Score: 70)
        if score < 70:
            all_target_kws = set(config.target_link_keywords or [])
            priority_kws = set(config.scraper_critical_priority_keywords or []) | set(config.scraper_high_priority_keywords or [])
            other_target_kws = all_target_kws - priority_kws
            if other_target_kws and any(kw in path_segments for kw in other_target_kws):
                score = 70
                if num_segments > config.scraper_max_keyword_path_segments:
                    score -= min(10, (num_segments - config.scraper_max_keyword_path_segments) * 3)

        # Tier 4: Any target keyword as a substring in a path segment (Score: 50)
        if score < 50 and config.target_link_keywords:
            if any(tk in seg for tk in config.target_link_keywords for seg in path_segments):
                score = max(score, 50)
        
        # Tier 5: Any target keyword in the link's visible text (Score: 40)
        if score < 40 and config.target_link_keywords:
            if any(tk in link_text for tk in config.target_link_keywords):
                score = max(score, 40)

        if score >= config.scraper_min_score_to_queue:
            log_text_snippet = link_text[:50].replace('\n', ' ')
            logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Link '{normalized_link_url}' scored: {score} (Text: '{log_text_snippet}...', Path: '{parsed_normalized_link.path}') - Adding to potential queue.")
            scored_links.append((normalized_link_url, score))
        else:
            log_text_snippet = link_text[:50].replace('\n', ' ')
            logger.debug(f"[RowID: {input_row_id}, Company: {company_name_or_id}] Link '{normalized_link_url}' (score {score}) below min_score_to_queue ({config.scraper_min_score_to_queue}). Path: '{parsed_normalized_link.path}', Text: '{log_text_snippet}...'. Discarding.")
            
    logger.info(f"[RowID: {input_row_id}, Company: {company_name_or_id}] From page {base_url}, found {len(scored_links)} internal links meeting score criteria.")
    return scored_links

def _classify_page_type(url_str: str, config: ScraperConfig) -> str:
    """Classifies a URL based on keywords in its path."""
    if not url_str:
        return "unknown"
    
    url_lower = url_str.lower()
    # Check for specific page types based on keywords in URL path
    # Order matters if keywords overlap; more specific should come first if necessary.
    # For now, assuming simple first-match.
    
    # Path-based classification
    parsed_url = urlparse(url_lower)
    path_lower = parsed_url.path

    # New page type classification
    if hasattr(config, 'page_type_keywords_about') and any(kw in path_lower for kw in config.page_type_keywords_about):
        return "about"
    if hasattr(config, 'page_type_keywords_product_service') and any(kw in path_lower for kw in config.page_type_keywords_product_service):
        return "product_service"
    # Add other new classifications here if needed, e.g.:
    # if hasattr(config, 'page_type_keywords_blog') and any(kw in path_lower for kw in config.page_type_keywords_blog):
    #     return "blog"

    # Fallback if no path keywords match, check full URL for very generic terms
    # (less reliable, path is usually better indicator for specific types)
    if hasattr(config, 'page_type_keywords_about') and any(kw in url_lower for kw in config.page_type_keywords_about):
        return "about"
    if hasattr(config, 'page_type_keywords_product_service') and any(kw in url_lower for kw in config.page_type_keywords_product_service):
        return "product_service"
    # Add other new classifications here for full URL check if needed

    # If it's just the base domain (e.g., http://example.com or http://example.com/)
    if not path_lower or path_lower == '/':
        return "homepage"

    return "general_content"

async def validate_link_status(url: str, http_client: httpx.AsyncClient) -> bool:
    """
    Validates the status of a URL by performing a HEAD request.

    Args:
        url: The URL to validate.
        http_client: An httpx.AsyncClient instance.

    Returns:
        True if the URL is valid (2xx status code), False otherwise.
    """
    try:
        response = await http_client.head(url, timeout=10, follow_redirects=True)
        if 200 <= response.status_code < 300:
            return True
        else:
            logger.warning(f"Skipping broken link (status {response.status_code}): {url}")
            return False
    except httpx.RequestError as e:
        logger.warning(f"Skipping link due to request error: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during link validation for {url}: {e}", exc_info=True)
        return False
def process_input_url(
    given_url_original: Optional[str],
    app_config_url_probing_tlds: List[str],
    row_identifier_for_log: str,
) -> Tuple[Optional[str], str]:
    """
    Processes an input URL by cleaning, performing TLD probing, and validating it.

    The function attempts to normalize the URL by adding a scheme if missing,
    removing spaces from the netloc, and quoting path/query/fragment.
    If the domain appears to lack a TLD (and is not 'localhost' or an IP address),
    it tries appending common TLDs from `app_config_url_probing_tlds` and
    checks for DNS resolution.

    Args:
        given_url_original: The original URL string from the input data.
        app_config_url_probing_tlds: A list of TLD strings (e.g., ["com", "org"])
                                     to try if the input URL seems to lack a TLD.
        row_identifier_for_log: A string identifier for logging, typically including
                                row index and company name, to contextualize log messages.
                                Example: "[RowID: 123, Company: ExampleCorp]"

    Returns:
        A tuple containing:
            - The processed and validated URL string if successful, otherwise None.
            - A status string: "Valid" if the URL is processed successfully,
              or "InvalidURL" if it's deemed invalid after processing.
    """
    processed_url: Optional[str] = given_url_original
    status: str = "Valid"

    if not given_url_original or not isinstance(given_url_original, str):
        logger.warning(
            f"{row_identifier_for_log} Input URL is missing or not a string: '{given_url_original}'"
        )
        return None, "InvalidURL"

    temp_url_stripped: str = given_url_original.strip()
    if not temp_url_stripped:
        logger.warning(
            f"{row_identifier_for_log} Input URL is empty after stripping: '{given_url_original}'"
        )
        return None, "InvalidURL"

    parsed_obj: ParseResult = urlparse(temp_url_stripped)
    current_scheme: str = parsed_obj.scheme
    current_netloc: str = parsed_obj.netloc
    current_path: str = parsed_obj.path
    current_params: str = parsed_obj.params
    current_query: str = parsed_obj.query
    current_fragment: str = parsed_obj.fragment

    # Ensure a scheme is present
    if not current_scheme:
        logger.info(
            f"{row_identifier_for_log} URL '{temp_url_stripped}' is schemeless. "
            f"Adding 'http://' and re-parsing."
        )
        temp_for_reparse_schemeless: str = "http://" + temp_url_stripped
        parsed_obj_schemed: ParseResult = urlparse(temp_for_reparse_schemeless)
        current_scheme = parsed_obj_schemed.scheme
        current_netloc = parsed_obj_schemed.netloc
        current_path = parsed_obj_schemed.path
        current_params = parsed_obj_schemed.params
        current_query = parsed_obj_schemed.query
        current_fragment = parsed_obj_schemed.fragment
        logger.debug(
            f"{row_identifier_for_log} After adding scheme: Netloc='{current_netloc}', Path='{current_path}'"
        )

    # Clean netloc (domain part)
    if " " in current_netloc:
        logger.info(
            f"{row_identifier_for_log} Spaces found in domain part '{current_netloc}'. Removing them."
        )
        current_netloc = current_netloc.replace(" ", "")

    # Safely quote URL components
    current_path = quote(current_path, safe='/%')
    current_query = quote(current_query, safe='=&amp;/?+%')  # Allow common query characters
    current_fragment = quote(current_fragment, safe='/?#%')  # Allow common fragment characters

    # TLD Probing Logic for domains that seem to lack a TLD
    # (e.g., "example" instead of "example.com")
    # Skips if it's 'localhost', an IP address, or already has a TLD-like pattern.
    if current_netloc and \
       not re.search(r'\.[a-zA-Z]{2,}$', current_netloc) and \
       not current_netloc.endswith('.'):
        is_ip_address = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", current_netloc)
        if current_netloc.lower() != 'localhost' and not is_ip_address:
            logger.info(
                f"{row_identifier_for_log} Domain '{current_netloc}' appears to lack a TLD. "
                f"Attempting TLD probing with {app_config_url_probing_tlds}..."
            )
            successfully_probed_tld: bool = False
            probed_netloc_base: str = current_netloc
            
            for tld_to_try in app_config_url_probing_tlds:
                candidate_domain_to_probe: str = f"{probed_netloc_base}.{tld_to_try}"
                logger.debug(f"{row_identifier_for_log} Probing: Trying '{candidate_domain_to_probe}'")
                try:
                    socket.gethostbyname(candidate_domain_to_probe) # Attempt DNS resolution
                    current_netloc = candidate_domain_to_probe
                    logger.info(
                        f"{row_identifier_for_log} TLD probe successful. "
                        f"Using '{current_netloc}' after trying '.{tld_to_try}'."
                    )
                    successfully_probed_tld = True
                    break  # Stop probing on first success
                except socket.gaierror:
                    logger.debug(
                        f"{row_identifier_for_log} TLD probe DNS lookup failed for '{candidate_domain_to_probe}'."
                    )
                except Exception as sock_e: # Catch other potential socket errors
                    logger.warning(
                        f"{row_identifier_for_log} TLD probe for '{candidate_domain_to_probe}' "
                        f"failed with unexpected socket error: {sock_e}"
                    )
            
            if not successfully_probed_tld:
                logger.warning(
                    f"{row_identifier_for_log} TLD probing failed for base domain '{probed_netloc_base}'. "
                    f"Proceeding with original/schemed netloc: '{current_netloc}'."
                )

    # Ensure path is at least '/' if netloc is present, otherwise empty
    effective_path: str = current_path if current_path else ('/' if current_netloc else '')
    
    # Reconstruct the URL from processed components
    processed_url = urlparse('')._replace(
        scheme=current_scheme, netloc=current_netloc, path=effective_path,
        params=current_params, query=current_query, fragment=current_fragment
    ).geturl()
    
    if processed_url != given_url_original:
        logger.info(
            f"{row_identifier_for_log} URL processed: Original='{given_url_original}', "
            f"Processed='{processed_url}'"
        )
    else:
        logger.info(
            f"{row_identifier_for_log} URL: Using original='{given_url_original}' (no changes after preprocessing)."
        )

    # Final validation: must have a scheme and be a string
    if not processed_url or not isinstance(processed_url, str) or \
       not processed_url.startswith(('http://', 'https://')):
        logger.warning(
            f"{row_identifier_for_log} Final URL is invalid: '{processed_url}' "
            f"(Original input was: '{given_url_original}')"
        )
        status = "InvalidURL"
        return None, status

    return processed_url, status