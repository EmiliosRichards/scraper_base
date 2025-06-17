import pytest
from playwright.async_api import async_playwright

from base_scraper.src.page_handler import fetch_page_content

@pytest.mark.asyncio
async def test_fetch_page_content_success(scraper_config, test_server):
    """
    Tests that fetch_page_content successfully retrieves content from a valid page.
    """
    url = f"{test_server}/index.html"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        content, status = await fetch_page_content(page, url, scraper_config, "test_id", "test_company")
        await browser.close()

        assert status == 200
        assert content is not None
        assert "<title>Test Site</title>" in content

@pytest.mark.asyncio
async def test_fetch_page_content_not_found(scraper_config, test_server):
    """
    Tests that fetch_page_content handles a 404 Not Found error correctly.
    """
    url = f"{test_server}/nonexistent.html"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        content, status = await fetch_page_content(page, url, scraper_config, "test_id", "test_company")
        await browser.close()

        assert status == 404
        assert content is None

@pytest.mark.asyncio
async def test_fetch_page_content_timeout(scraper_config):
    """
    Tests that fetch_page_content handles a navigation timeout correctly.
    """
    # This URL should be non-responsive to trigger a timeout
    url = "http://localhost:9999"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # Set a very short timeout for the test
        scraper_config.default_navigation_timeout = 1000
        content, status = await fetch_page_content(page, url, scraper_config, "test_id", "test_company")
        await browser.close()

        assert status == -1  # Timeout code
        assert content is None

@pytest.mark.asyncio
async def test_fetch_page_content_dns_error(scraper_config):
    """
    Tests that fetch_page_content handles a DNS resolution error correctly.
    """
    url = "http://nonexistent-domain-for-testing.com"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        content, status = await fetch_page_content(page, url, scraper_config, "test_id", "test_company")
        await browser.close()

        assert status == -2  # DNS error code
        assert content is None