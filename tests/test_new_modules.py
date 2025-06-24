import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from base_scraper.src.config import ScraperConfig
from base_scraper.src.proxy_manager import ProxyManager
from base_scraper.src.interaction_handler import InteractionHandler
from base_scraper.src.captcha_solver import get_captcha_solver, TwoCaptchaSolver

@pytest.fixture
def config():
    """Provides a mock ScraperConfig object."""
    mock_config = ScraperConfig()
    # Override defaults for testing
    mock_config.proxy_list = ["http://proxy1:8080", "http://proxy2:8080"]
    mock_config.proxy_health_check_enabled = True
    mock_config.proxy_cooldown_seconds = 10
    mock_config.interaction_selectors = ["#cookie-accept"]
    mock_config.interaction_text_queries = ["Accept All"]
    mock_config.captcha_solver_enabled = True
    mock_config.captcha_provider = '2captcha'
    mock_config.captcha_api_key = 'test_key'
    mock_config.interaction_handler_timeout_seconds = 10
    return mock_config

# --- ProxyManager Tests ---
def test_proxy_manager_init(config):
    pm = ProxyManager(config)
    assert len(pm.proxies) == 2
    assert "http://proxy1:8080" in pm.proxy_health

def test_proxy_manager_get_proxy_random(config):
    config.proxy_rotation_strategy = 'random'
    pm = ProxyManager(config)
    proxy = pm.get_proxy()
    assert proxy in config.proxy_list

def test_proxy_manager_get_proxy_sequential(config):
    config.proxy_rotation_strategy = 'sequential'
    pm = ProxyManager(config)
    p1 = pm.get_proxy()
    p2 = pm.get_proxy()
    p3 = pm.get_proxy()
    assert p1 == "http://proxy1:8080"
    assert p2 == "http://proxy2:8080"
    assert p3 == "http://proxy1:8080" # Wraps around

def test_proxy_manager_failure_and_cooldown(config, mocker):
    mocker.patch('time.time', return_value=100)
    pm = ProxyManager(config)
    
    # Report failure
    pm.report_failure("http://proxy1:8080")
    assert pm.proxy_health["http://proxy1:8080"]['status'] == 'unhealthy'
    
    # Should only get the healthy proxy
    proxy = pm.get_proxy()
    assert proxy == "http://proxy2:8080"
    
    # Simulate time passing for cooldown
    mocker.patch('time.time', return_value=115) # 15 seconds later
    
    # Now it should be healthy again
    proxy = pm.get_proxy()
    assert "http://proxy1:8080" in pm.proxy_health
    assert pm.proxy_health["http://proxy1:8080"]['status'] == 'healthy'


# --- InteractionHandler and CaptchaSolver Tests ---
@pytest.mark.asyncio
async def test_interaction_handler(config):
    mock_page = AsyncMock()

    # --- Mock for selector ---
    selector_locator = AsyncMock()
    # Make the selector element disappear after one click
    selector_visibility = [True, False]
    selector_locator.is_visible = AsyncMock(side_effect=lambda *a, **kw: selector_visibility.pop(0) if selector_visibility else False)
    selector_locator.click = AsyncMock()
    selector_container = MagicMock()
    selector_container.first = selector_locator

    # --- Mock for text ---
    text_locator = AsyncMock()
    # Make the text element disappear after one click
    text_visibility = [True, False]
    text_locator.is_visible = AsyncMock(side_effect=lambda *a, **kw: text_visibility.pop(0) if text_visibility else False)
    text_locator.click = AsyncMock()
    text_container = MagicMock()
    text_container.first = text_locator

    # --- Side effect for page.locator ---
    def locator_side_effect(selector):
        if selector == "#cookie-accept":
            return selector_container
        elif selector == f"*:visible:text-is('{config.interaction_text_queries[0]}')":
            return text_container
        else:
            m = MagicMock()
            m.first.is_visible.return_value = False
            return m

    mock_page.locator = MagicMock(side_effect=locator_side_effect)

    handler = InteractionHandler(mock_page, config)
    await handler.handle_interactions()

    # Assertions
    mock_page.locator.assert_any_call("#cookie-accept")
    mock_page.locator.assert_any_call(f"*:visible:text-is('{config.interaction_text_queries[0]}')")
    assert selector_locator.click.call_count == 1
    assert text_locator.click.call_count == 1

@pytest.mark.asyncio
async def test_captcha_solver_factory(config):
    mock_page = AsyncMock()
    solver = get_captcha_solver(mock_page, config)
    assert isinstance(solver, TwoCaptchaSolver)

    config.captcha_solver_enabled = False
    solver = get_captcha_solver(mock_page, config)
    assert solver is None

@pytest.mark.asyncio
async def test_captcha_detector(config):
    mock_page = AsyncMock()

    # The final locator object that has the async `wait_for` method.
    final_locator = MagicMock()
    final_locator.wait_for = AsyncMock()

    # The intermediate locator returned by `frame_locator.locator()`
    intermediate_locator = MagicMock()
    intermediate_locator.locator.return_value = final_locator

    # Replace `frame_locator` on the page mock with a sync mock
    mock_page.frame_locator = MagicMock(return_value=intermediate_locator)

    solver = TwoCaptchaSolver(mock_page, config)

    # Test case 1: Captcha detected
    final_locator.wait_for.side_effect = None
    detected = await solver.detect_captcha()
    assert detected is True

    # Test case 2: Captcha not detected (timeout)
    final_locator.wait_for.side_effect = PlaywrightTimeoutError("Timeout")
    detected = await solver.detect_captcha()
    assert detected is False
# --- Integration Tests ---
@pytest.mark.asyncio
async def test_full_integration_with_interaction_handler(config):
    """
    Tests the full scrape flow with the interaction handler on a live page.
    """
    from base_scraper.src.scraper import scrape_website
    import os
    from pathlib import Path
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    # Point to the local test file using pathlib for robustness
    test_file_path = Path(__file__).parent / "test_site" / "cookie_banner.html"
    test_url = test_file_path.as_uri()

    # Enable interaction handler, disable others
    config.interaction_handler_enabled = True
    config.proxy_enabled = False
    config.captcha_solver_enabled = False
    # Add the specific selector for the test file
    config.interaction_selectors = ["#cookie-banner #accept-cookies"]
    config.interaction_text_queries = []


    output_dir = 'test_output_integration'
    results = await scrape_website(test_url, config, output_dir, "integration_test_company")

    # The scrape should succeed and return one page result
    assert len(results) == 1
    assert results[0]['status'] == 200
    assert "Page with a Cookie Banner" in results[0]['summary_text']

    # Cleanup
    import shutil
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)