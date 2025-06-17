import pytest
from unittest.mock import MagicMock, patch
import httpx

from base_scraper.src.utils import (
    normalize_url,
    get_safe_filename,
    extract_text_from_html,
    find_internal_links,
    _classify_page_type,
    validate_link_status,
    process_input_url,
)

# --- Tests for normalize_url ---

@pytest.mark.parametrize("url, expected", [
    ("http://example.com", "http://example.com/"),
    ("http://www.example.com", "http://example.com/"),
    ("https://example.com/path/", "https://example.com/path"),
    ("http://example.com/index.html", "http://example.com/"),
    ("http://example.com/path?b=2&a=1", "http://example.com/path?a=1&b=2"),
    ("http://example.com/path#fragment", "http://example.com/path"),
    ("http://example.com/?fallback=true", "http://example.com/"),
])
def test_normalize_url(url, expected):
    assert normalize_url(url) == expected

# --- Tests for get_safe_filename ---

def test_get_safe_filename_for_url(scraper_config):
    url = "http://www.example.com/some/path"
    expected = "examplec_20130b4c"
    assert get_safe_filename(url, scraper_config, for_url=True) == expected

def test_get_safe_filename_for_company(scraper_config):
    company_name = "My Awesome Company, Inc."
    expected = "My_Awesome_Company__Inc."
    assert get_safe_filename(company_name, scraper_config, for_url=False) == expected

# --- Tests for extract_text_from_html ---

def test_extract_text_from_html():
    html = "<html><head><title>Test</title><script>alert('hi')</script></head><body><p>Hello World</p></body></html>"
    expected = "Test Hello World"
    assert extract_text_from_html(html) == expected

# --- Tests for find_internal_links ---

def test_find_internal_links(scraper_config, test_server):
    html = f'<html><body><a href="{test_server}/about.html">About Us</a></body></html>'
    base_url = f"{test_server}/"
    links = find_internal_links(html, base_url, scraper_config, "test_id", "test_company")
    assert len(links) == 1
    assert links[0][0] == f"{test_server}/about.html"

# --- Tests for _classify_page_type ---

@pytest.mark.parametrize("url, expected_type", [
    ("http://example.com/about-us", "about"),
    ("http://example.com/products/widget", "product_service"),
    ("http://example.com/", "homepage"),
    ("http://example.com/blog/post", "general_content"),
])
def test_classify_page_type(url, expected_type, scraper_config):
    assert _classify_page_type(url, scraper_config) == expected_type

# --- Tests for validate_link_status ---

@pytest.mark.asyncio
async def test_validate_link_status_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.head.return_value = mock_response
    assert await validate_link_status("http://example.com", mock_client) is True

@pytest.mark.asyncio
async def test_validate_link_status_failure():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.head.return_value = mock_response
    assert await validate_link_status("http://example.com/404", mock_client) is False

# --- Tests for process_input_url ---

@patch('socket.gethostbyname')
def test_process_input_url_tld_probing(mock_gethostbyname):
    mock_gethostbyname.return_value = "127.0.0.1"
    url, status = process_input_url("example", ["com", "de"], "test_id")
    assert url == "http://example.com/"
    assert status == "Valid"

def test_process_input_url_no_probing():
    url, status = process_input_url("http://example.com", [], "test_id")
    assert url == "http://example.com/"
    assert status == "Valid"

def test_process_input_url_invalid():
    url, status = process_input_url("", [], "test_id")
    assert url is None
    assert status == "InvalidURL"