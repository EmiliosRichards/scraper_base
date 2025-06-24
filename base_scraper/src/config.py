import os
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables from a .env file.
# This allows for flexible configuration without hardcoding values.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class ScraperConfig:
    """
    Manages all configurations for the standalone web scraper module.

    Settings are loaded from environment variables with sensible defaults, allowing for
    easy customization of the scraper's behavior without modifying the codebase.
    """

    def __init__(self):
        """
        Initializes the ScraperConfig instance by loading values from environment
        variables or using predefined defaults.
        """
        # --- Core Scraping Parameters ---
        self.user_agent: str = os.getenv('SCRAPER_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.default_page_timeout: int = int(os.getenv('SCRAPER_PAGE_TIMEOUT_MS', '30000'))
        self.default_navigation_timeout: int = int(os.getenv('SCRAPER_NAVIGATION_TIMEOUT_MS', '60000'))
        self.scrape_max_retries: int = int(os.getenv('SCRAPER_MAX_RETRIES', '2'))
        self.scrape_retry_delay_seconds: int = int(os.getenv('SCRAPER_RETRY_DELAY_SECONDS', '5'))
        self.max_depth_internal_links: int = int(os.getenv('MAX_DEPTH_INTERNAL_LINKS', '1'))
        self.scraper_networkidle_timeout_ms: int = int(os.getenv('SCRAPER_NETWORKIDLE_TIMEOUT_MS', '3000'))

        # --- Link Prioritization and Filtering ---
        target_link_keywords_str: str = os.getenv('TARGET_LINK_KEYWORDS', 'about,company,services,products,solutions,team,mission,contact,imprint,datenschutz,impressum,ueber-uns,ueber_uns,kontakt')
        self.target_link_keywords: List[str] = [kw.strip().lower() for kw in target_link_keywords_str.split(',') if kw.strip()]

        critical_priority_keywords_str: str = os.getenv('SCRAPER_CRITICAL_PRIORITY_KEYWORDS', 'impressum,imprint,about-us,about_us,ueber-uns,ueber_uns')
        self.scraper_critical_priority_keywords: List[str] = [kw.strip().lower() for kw in critical_priority_keywords_str.split(',') if kw.strip()]

        high_priority_keywords_str: str = os.getenv('SCRAPER_HIGH_PRIORITY_KEYWORDS', 'services,products,solutions,leistungen,produkte')
        self.scraper_high_priority_keywords: List[str] = [kw.strip().lower() for kw in high_priority_keywords_str.split(',') if kw.strip()]

        exclude_link_patterns_str: str = os.getenv('SCRAPER_EXCLUDE_LINK_PATH_PATTERNS', '/media/,/blog/,/wp-content/,/video/,/news/')
        self.scraper_exclude_link_path_patterns: List[str] = [p.strip().lower() for p in exclude_link_patterns_str.split(',') if p.strip()]

        # --- Scraping Limits and Scoring ---
        self.scraper_max_pages_per_domain: int = int(os.getenv('SCRAPER_MAX_PAGES_PER_DOMAIN', '20'))
        self.scraper_min_score_to_queue: int = int(os.getenv('SCRAPER_MIN_SCORE_TO_QUEUE', '40'))
        self.scraper_score_threshold_for_limit_bypass: int = int(os.getenv('SCRAPER_SCORE_THRESHOLD_FOR_LIMIT_BYPASS', '80'))
        self.scraper_max_high_priority_pages_after_limit: int = int(os.getenv('SCRAPER_MAX_HIGH_PRIORITY_PAGES_AFTER_LIMIT', '5'))
        self.scraper_max_keyword_path_segments: int = int(os.getenv('SCRAPER_MAX_KEYWORD_PATH_SEGMENTS', '3'))

        # --- Content and Summary ---
        self.scraper_pages_for_summary_count: int = int(os.getenv('SCRAPER_PAGES_FOR_SUMMARY_COUNT', '3'))
        self.llm_max_input_chars_for_summary: int = int(os.getenv('LLM_MAX_INPUT_CHARS_FOR_SUMMARY', '40000'))

        # --- Output and Filenames ---
        self.output_base_dir: str = os.getenv('OUTPUT_BASE_DIR', 'output_data')
        self.scraped_content_subdir: str = 'scraped_content'
        self.filename_company_name_max_len: int = int(os.getenv('FILENAME_COMPANY_NAME_MAX_LEN', '25'))
        self.filename_url_domain_max_len: int = int(os.getenv('FILENAME_URL_DOMAIN_MAX_LEN', '8'))
        self.filename_url_hash_max_len: int = int(os.getenv('FILENAME_URL_HASH_MAX_LEN', '8'))

        # --- Robots.txt Handling ---
        self.respect_robots_txt: bool = os.getenv('RESPECT_ROBOTS_TXT', 'True').lower() == 'true'
        self.robots_txt_user_agent: str = os.getenv('ROBOTS_TXT_USER_AGENT', '*')

        # --- URL Probing and Fallbacks ---
        url_probing_tlds_str: str = os.getenv('URL_PROBING_TLDS', 'de,com,at,ch')
        self.url_probing_tlds: List[str] = [tld.strip().lower() for tld in url_probing_tlds_str.split(',') if tld.strip()]
        self.enable_dns_error_fallbacks: bool = os.getenv('ENABLE_DNS_ERROR_FALLBACKS', 'True').lower() == 'true'

        # --- Page Type Classification ---
        page_type_about_str: str = os.getenv('PAGE_TYPE_KEYWORDS_ABOUT', 'about,about-us,company,profile,mission,vision,team,ueber-uns,ueber_uns,unternehmen')
        self.page_type_keywords_about: List[str] = [kw.strip().lower() for kw in page_type_about_str.split(',') if kw.strip()]

        page_type_product_service_str: str = os.getenv('PAGE_TYPE_KEYWORDS_PRODUCT_SERVICE', 'products,services,solutions,offerings,platform,features,produkte,leistungen,loesungen')
        self.page_type_keywords_product_service: List[str] = [kw.strip().lower() for kw in page_type_product_service_str.split(',') if kw.strip()]

# --- Caching ---
        self.caching_enabled: bool = os.getenv('CACHING_ENABLED', 'True').lower() == 'true'
        self.cache_dir: str = os.getenv('CACHE_DIR', 'cache')
        # --- Proxy Management ---
        self.proxy_enabled: bool = os.getenv('PROXY_ENABLED', 'False').lower() == 'true'
        self.proxy_list: List[str] = [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]
        self.proxy_rotation_strategy: str = os.getenv('PROXY_ROTATION_STRATEGY', 'random') # 'random', 'sequential', 'rotate_on_failure'
        self.proxy_health_check_enabled: bool = os.getenv('PROXY_HEALTH_CHECK_ENABLED', 'True').lower() == 'true'
        self.proxy_cooldown_seconds: int = int(os.getenv('PROXY_COOLDOWN_SECONDS', '300'))

        # --- Interaction Handling ---
        self.interaction_handler_enabled: bool = os.getenv('INTERACTION_HANDLER_ENABLED', 'True').lower() == 'true'
        interaction_selectors_str: str = os.getenv('INTERACTION_SELECTORS', 'button[id*="accept"],button[id*="agree"],button[id*="consent"],button[id*="cookie"]')
        self.interaction_selectors: List[str] = [s.strip() for s in interaction_selectors_str.split(',') if s.strip()]
        interaction_text_queries_str: str = os.getenv('INTERACTION_TEXT_QUERIES', 'Accept all,Agree,Consent,I agree')
        self.interaction_text_queries: List[str] = [q.strip() for q in interaction_text_queries_str.split(',') if q.strip()]
        self.interaction_handler_timeout_seconds: int = int(os.getenv('INTERACTION_HANDLER_TIMEOUT_SECONDS', '5'))

        # --- CAPTCHA Solving ---
        self.captcha_solver_enabled: bool = os.getenv('CAPTCHA_SOLVER_ENABLED', 'False').lower() == 'true'
        self.captcha_provider: str = os.getenv('CAPTCHA_PROVIDER', '2captcha')
        self.captcha_api_key: Optional[str] = os.getenv('CAPTCHA_API_KEY')