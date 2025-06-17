import pytest
import http.server
import socketserver
import threading
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing from base_scraper
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from base_scraper.src.config import ScraperConfig

@pytest.fixture(scope="session")
def scraper_config():
    """
    Provides a ScraperConfig instance for tests.
    """
    return ScraperConfig()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files from the tests/test_site directory
        super().__init__(*args, directory=str(project_root / "tests" / "test_site"), **kwargs)

@pytest.fixture(scope="session")
def test_server():
    """
    Starts a local HTTP server to serve the test site.
    """
    PORT = 8000
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        yield f"http://localhost:{PORT}"
        httpd.shutdown()