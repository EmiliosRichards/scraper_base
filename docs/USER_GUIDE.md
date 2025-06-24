# How to Use the Scraper: A Step-by-Step Guide

This guide will walk you through setting up the environment, configuring the scraper—including its powerful new features—and running it. For complete and up-to-date documentation, always refer to the `base_scraper/README.md` file.

---

## 1. Initial Setup

First, you need to set up a dedicated environment for the scraper to ensure all its dependencies are managed correctly.

1.  **Create a Virtual Environment:**
    Open your terminal, navigate to the project's root directory, and run the following commands. This isolates the project's dependencies.

    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```

2.  **Install Required Packages:**
    With your virtual environment active, install the necessary Python packages using the `requirements.txt` file.

    ```bash
    pip install -r base_scraper/requirements.txt
    ```

---

## 2. Configuration

The scraper's behavior is controlled by environment variables. You'll set these in a `.env` file.

1.  **Create the `.env` File:**
    In the `base_scraper/` directory, make a copy of the `.env.example` file and name it `.env`.

2.  **Configure Scraper Settings:**
    Open the new `.env` file with a text editor. It contains all the configuration options for the scraper. Below is a detailed explanation of how to configure the new advanced features.

    #### Advanced Feature Configuration

    These features help the scraper navigate modern web protections and can be enabled or disabled as needed.

    **A. IP Rotation (Proxy Management)**
    To avoid being blocked, you can route the scraper's traffic through multiple proxy servers.

    *   `PROXY_ENABLED`: Set to `True` to turn on proxy usage.
    *   `PROXY_LIST`: Provide a comma-separated list of your proxy URLs.
        *   **Example:** `PROXY_LIST="http://user:pass@proxy1.com:8080,http://user:pass@proxy2.com:8080"`
    *   `PROXY_ROTATION_STRATEGY`: Choose how proxies are selected. Options are `random` (default), `sequential`, or `rotate_on_failure`.

    **B. Proactive Interaction Handling**
    This feature automatically dismisses common website interruptions like cookie banners or pop-ups. It is enabled by default.

    *   `INTERACTION_HANDLER_ENABLED`: Set to `True` to keep it active or `False` to disable it.
    *   `INTERACTION_SELECTORS`: A comma-separated list of CSS selectors for elements to click (e.g., `#accept-cookies, .close-button`).
    *   `INTERACTION_TEXT_QUERIES`: A comma-separated list of text to find within clickable elements (e.g., `Accept all, I agree`).

    **C. Third-Party CAPTCHA Solving**
    Integrate with a CAPTCHA-solving service to handle challenges automatically.

    *   `CAPTCHA_SOLVER_ENABLED`: Set to `True` to enable this feature.
    *   `CAPTCHA_PROVIDER`: Specify the service provider (e.g., `2captcha`).
    *   `CAPTCHA_API_KEY`: Enter your API key for the chosen service.
        *   **Example:** `CAPTCHA_API_KEY="your_actual_api_key_here"`

---

## 3. Execution

Once your setup and configuration are complete, you can run the scraper.

1.  **Run the Main Script:**
    From the root directory of the project, execute the following command in your terminal (ensure your virtual environment is still active):

    ```bash
    python base_scraper/main.py