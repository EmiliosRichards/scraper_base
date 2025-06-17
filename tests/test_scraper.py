import pytest
import os
from unittest.mock import patch

from base_scraper.src.scraper import scrape_website

@pytest.mark.asyncio
async def test_scrape_website_successful_crawl(scraper_config, test_server, tmp_path):
    """
    Tests a successful crawl of the local test site.
    """
    url = f"{test_server}/index.html"
    output_dir = str(tmp_path)
    results = await scrape_website(url, scraper_config, output_dir, "test_company")

    assert len(results) == 3  # index.html, about.html, contact.html
    urls = {r['url'] for r in results}
    assert f"{test_server}/" in urls
    assert f"{test_server}/about.html" in urls
    assert f"{test_server}/contact.html" in urls
    assert f"{test_server}/disallowed.html" not in urls

@pytest.mark.asyncio
async def test_scrape_website_respects_robots_txt(scraper_config, test_server, tmp_path):
    """
    Tests that the scraper respects the robots.txt file.
    """
    url = f"{test_server}/index.html"
    scraper_config.respect_robots_txt = True
    output_dir = str(tmp_path)
    
    # This will still crawl index, about, and contact, but the assertion is that it doesn't touch disallowed.html
    results = await scrape_website(url, scraper_config, output_dir, "test_company")
    
    urls = {r['url'] for r in results}
    assert f"{test_server}/disallowed.html" not in urls

@pytest.mark.asyncio
async def test_scrape_website_page_limit(scraper_config, test_server, tmp_path):
    """
    Tests that the scraper respects the page limit.
    """
    url = f"{test_server}/index.html"
    scraper_config.scraper_max_pages_per_domain = 1
    output_dir = str(tmp_path)
    results = await scrape_website(url, scraper_config, output_dir, "test_company")

    assert len(results) == 1
    assert results[0]['url'] == f"{test_server}/"

@pytest.mark.asyncio
@patch('base_scraper.src.scraper.process_input_url')
async def test_scrape_website_dns_fallback(mock_process_input_url, scraper_config, test_server, tmp_path):
    """
    Tests the DNS fallback mechanism by mocking the process_input_url function.
    """
    # Simulate a DNS error on the initial URL, but have the fallback succeed.
    mock_process_input_url.return_value = (f"{test_server}/index.html", "Valid")
    
    # The initial URL is fake, but the mock will return the valid test server URL
    initial_url = "http://nonexistent-domain-for-testing.com"
    output_dir = str(tmp_path)
    
    results = await scrape_website(initial_url, scraper_config, output_dir, "test_company")

    # The mock should allow the scraper to proceed and crawl the test site
    assert len(results) > 0
    assert results[0]['url'].startswith(test_server)