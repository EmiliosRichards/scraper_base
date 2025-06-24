# Base Scraper

A flexible and robust web scraper for various data extraction tasks.

## Setup

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file:**
    Create a `.env` file in the `base_scraper` directory by copying the `.env.example` file.

2.  **Fill in the environment variables:**
    Open the `.env` file and provide the necessary values for the variables listed. These variables are used to configure the scraper's behavior.

## Usage

To run the scraper, execute the `main.py` script:

```bash
python base_scraper/main.py
```

The script will use the settings from your `.env` file to perform the scraping tasks.
## Testing

This project uses `pytest` for testing. The test suite includes unit tests, integration tests, and end-to-end tests.

### Setup for Testing

1.  **Install development dependencies:**
    Make sure you have activated your virtual environment, then run:
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Install Playwright browsers:**
    The tests require Playwright's browser binaries. Install them with:
    ```bash
    playwright install
    ```

### Running the Tests

To run the entire test suite, use the following command from the root directory of the project:

```bash
pytest
```
## Advanced Features

The scraper includes several advanced features to handle modern anti-bot measures and improve success rates. These are all configurable via environment variables in your `.env` file.

### IP Rotation (Proxy Management)

To prevent IP-based blocking, the scraper can rotate through a list of proxies.

*   **`PROXY_ENABLED`**: Set to `True` to enable this feature.
*   **`PROXY_LIST`**: A comma-separated list of proxy server URLs (e.g., `http://user:pass@host1:port,http://user:pass@host2:port`).
*   **`PROXY_ROTATION_STRATEGY`**: How to rotate proxies. Can be `random` (default), `sequential`, or `rotate_on_failure`.
*   **`PROXY_HEALTH_CHECK_ENABLED`**: Set to `True` (default) to automatically sideline failing proxies.
*   **`PROXY_COOLDOWN_SECONDS`**: The number of seconds a failing proxy will be sidelined before being retried (default: `300`).

### Proactive Interaction Handling

This feature attempts to automatically dismiss overlays like cookie consent banners and newsletter pop-ups.

*   **`INTERACTION_HANDLER_ENABLED`**: Set to `True` (default) to enable this feature.
*   **`INTERACTION_SELECTORS`**: A comma-separated list of CSS selectors to identify clickable elements on modals (e.g., `#accept-cookies,[aria-label='close']`).
*   **`INTERACTION_TEXT_QUERIES`**: A comma-separated list of text strings to find on clickable elements (e.g., `Accept all,I agree`).
*   **`INTERACTION_HANDLER_TIMEOUT_SECONDS`**: How long the handler will search for modals before giving up (default: `5`).

### Third-Party CAPTCHA Solving

The scraper can integrate with third-party services to solve CAPTCHAs.

*   **`CAPTCHA_SOLVER_ENABLED`**: Set to `True` to enable this feature.
*   **`CAPTCHA_PROVIDER`**: The service to use. Currently supports `2captcha` (default).
*   **`CAPTCHA_API_KEY`**: Your API key for the chosen CAPTCHA solving service.