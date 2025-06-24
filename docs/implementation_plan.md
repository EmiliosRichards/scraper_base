# **Enhanced Implementation Plan (Granular Breakdown)**

This document outlines the step-by-step plan to enhance the scraper, breaking down complex tasks into smaller sub-tasks for a more manageable implementation process.

**1. Foundational Modules (Overall Difficulty: 3/10)**

*   **Task 1.1 (Difficulty: 3/10):** Create `interaction_handler.py`, `proxy_manager.py`, and `captcha_solver.py` with their respective placeholder class structures (`InteractionHandler`, `ProxyManager`, `BaseCaptchaSolver`).

**2. Centralized Configuration (`config.py`) (Overall Difficulty: 3/10)**

*   **Task 2.1 (Difficulty: 3/10):** Add all new configuration properties to the `ScraperConfig` class in `base_scraper/src/config.py`, loading them from environment variables with sensible defaults.

**3. Enhanced Proxy Management (`proxy_manager.py`) (Overall Difficulty: 7/10)**

*   **Task 3.1 - Basic Structure (Difficulty: 3/10):** Implement the `ProxyManager` class to load proxies from the config and include basic `sequential` and `random` rotation strategies.
*   **Task 3.2 - Health Checks (Overall Difficulty: 4/10):**
    *   **Task 3.2.1 (Difficulty: 2/10):** Add a data structure within `ProxyManager` (e.g., a dictionary or a list of objects) to store each proxy's URL, its current health status (`healthy`, `unhealthy`), and the timestamp of its last failure.
    *   **Task 3.2.2 (Difficulty: 2/10):** Create an internal method `_mark_unhealthy(proxy_url)` that updates the proxy's status and failure timestamp. The main `get_proxy` method will call this when an error is reported.
*   **Task 3.3 - Cooldown Logic (Difficulty: 3/10):** Implement the cooldown timer. When a proxy is marked unhealthy, it should be sidelined for a configurable duration before being returned to the active pool.

**4. Robust Interaction Handling (`interaction_handler.py`) (Overall Difficulty: 6/10)**

*   **Task 4.1 - Core Handler Loop (Difficulty: 3/10):** Implement the main handler loop that iterates through CSS selectors from the config and attempts to click the corresponding elements.
*   **Task 4.2 - Text-Based Detection (Difficulty: 3/10):** Enhance the handler to also search for elements containing specific text strings, providing a more resilient detection method.
*   **Task 4.3 - Safety Timeout (Difficulty: 2/10):** Add an overall timeout to the handler's loop to prevent it from stalling the entire scraping process.

**5. Abstracted CAPTCHA Solving (`captcha_solver.py`) (Overall Difficulty: 8/10)**

*   **Task 5.1 - Abstract Base Class (Difficulty: 3/10):** Define the `BaseCaptchaSolver` ABC with abstract methods like `detect_captcha()` and `solve_captcha()` to enforce a standard interface.
*   **Task 5.2 - Concrete Implementation (Overall Difficulty: 5/10):**
    *   **Task 5.2.1 (Difficulty: 3/10):** Implement the method to send the CAPTCHA task to the third-party API. This involves making the initial HTTP request with the site key and page URL.
    *   **Task 5.2.2 (Difficulty: 3/10):** Implement the polling mechanism to periodically check the API for the solution token, handling the delay between checks.
*   **Task 5.3 - Factory and Error Handling (Difficulty: 3/10):** Build a factory function to instantiate the correct solver based on the config. Implement robust error handling for API failures, timeouts, and invalid solution tokens.

**6. Intelligent Integration and Refactoring (Overall Difficulty: 7/10)**

*   **Task 6.1 - Integrate Proxy Manager (Overall Difficulty: 4/10):**
    *   **Task 6.1.1 (Difficulty: 2/10):** In `scraper.py`, import and initialize the `ProxyManager`.
    *   **Task 6.1.2 (Difficulty: 2/10):** Modify the `playwright.chromium.launch()` call to include the `proxy` argument with a server URL obtained from the `ProxyManager`.
*   **Task 6.2 - Refactor `page_handler.py` (Overall Difficulty: 5/10):**
    *   **Task 6.2.1 (Difficulty: 2/10):** Define custom exception classes or a set of specific error codes/tuples (e.g., `ProxyError`, `CaptchaFailed`) to represent different failure scenarios.
    *   **Task 6.2.2 (Difficulty: 3/10):** Modify the `try...except` blocks within `fetch_page_content` to catch errors from the new handlers and return the appropriate custom error type instead of generic status codes.
    *   **Task 6.2.3 (Difficulty: 2/10):** Add the orchestration logic to call the interaction and CAPTCHA handlers in the correct sequence after `page.goto()`.
*   **Task 6.3 - Context-Aware Retries (Overall Difficulty: 4/10):**
    *   **Task 6.3.1 (Difficulty: 2/10):** In `scraper.py`, modify the `except` block in the retry loop to catch the new specific error types from `page_handler`.
    *   **Task 6.3.2 (Difficulty: 2/10):** Implement the conditional logic. If a `ProxyError` is caught, call a method on the `ProxyManager` to report the failure before retrying. If a `CaptchaFailed` error is caught, log it and break the loop.

**7. Comprehensive Testing Strategy (Overall Difficulty: 5/10)**

*   **Task 7.1 - Create Test Assets (Difficulty: 2/10):** Create simple, static HTML files in `tests/test_site/` that contain mock cookie banners and CAPTCHA elements for testing.
*   **Task 7.2 - Unit Test Modules (Overall Difficulty: 4/10):**
    *   **Task 7.2.1 (Difficulty: 2/10):** Write unit tests for `ProxyManager`, mocking the proxy list and verifying rotation and health check logic.
    *   **Task 7.2.2 (Difficulty: 2/10):** Write unit tests for `InteractionHandler` and `CaptchaSolver`, using `pytest-mock` to simulate Playwright page objects and API responses.
*   **Task 7.3 - Integration Tests (Difficulty: 3/10):** Write integration tests that use the test assets to verify that the handlers work together as expected.

---
### **Architectural Flow Diagram**

(The diagram remains the same as it represents the high-level architecture.)

```mermaid
graph TD
    subgraph Scraper Orchestration
        A[scrape_website in scraper.py] --> B{Proxy Enabled?};
        B -- Yes --> C[Get Healthy Proxy from ProxyManager];
        C --> D[Launch Browser with Proxy];
        B -- No --> E[Launch Browser Directly];
        D & E --> F[Call _perform_scrape_for_entry_point];
    end

    subgraph Page Handling and Pre-Scrape Checks
        F --> G[fetch_page_content in page_handler.py];
        G --> H{Interaction Handling Enabled?};
        H -- Yes --> I[Invoke Interaction Handler Loop];
        I --> J{CAPTCHA Detected?};
        H -- No --> J;
        J -- Yes --> K[Invoke CAPTCHA Solver];
        K --> L[Extract Page Content];
        J -- No --> L;
    end

    subgraph New Support Modules
        C --> PM[proxy_manager.py];
        I --> IH[interaction_handler.py];
        K --> CS[captcha_solver.py];
    end

    subgraph Configuration
        CONF[config.py] --> B;
        CONF --> H;
        CONF --> J;
        CONF --> PM;
    end