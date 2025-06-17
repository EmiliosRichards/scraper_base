# Detailed Testing Plan for `base_scraper`

This document outlines a comprehensive, four-phase plan to build a robust test suite for the `base_scraper` module using the `pytest` framework. The goal is to cover unit, integration, and end-to-end testing scenarios to ensure the scraper's reliability and correctness.

---

## **Phase 1: Setup and Test Infrastructure**
**Objective:** To establish the foundational structure, tools, and reusable components for our test suite.

*   **Task 1.1: Introduce Testing Framework and Directory Structure**
    *   **Difficulty:** 2/10
    *   **What:** We will introduce `pytest` as our testing framework and create a dedicated `tests/` directory.
    *   **Why:** A dedicated `tests/` directory keeps test code separate from application code. `pytest` is a powerful and standard Python testing tool.
    *   **How:** We will create a `requirements-dev.txt` file and add `pytest`, `pytest-playwright`, and `pytest-mock`. We will then create the `tests/` directory.

*   **Task 1.2: Create a Local Test Website**
    *   **Difficulty:** 3/10
    *   **What:** We will create a small, self-contained set of HTML files within a `tests/test_site/` directory.
    *   **Why:** A local test site provides a controlled, predictable environment for testing, eliminating reliance on external websites.
    *   **How:** We will write simple HTML files (`index.html`, `about.html`, `contact.html`, `disallowed.html`) with varying content and links, plus a `robots.txt` file that disallows access to `disallowed.html`.

*   **Task 1.3: Create Core Pytest Fixtures**
    *   **Difficulty:** 4/10
    *   **What:** Create a `tests/conftest.py` file to house reusable test fixtures.
    *   **Why:** Fixtures allow us to set up common test conditions (like a configured `ScraperConfig` object or a running web server for our test site) once and reuse them across multiple tests, making the test code cleaner and more maintainable.
    *   **How:** We will create a fixture that provides a default `ScraperConfig` instance for tests. We will also create a fixture that starts a simple local HTTP server to serve the files from our `tests/test_site/` directory.

---

## **Phase 2: Unit Testing (Testing Functions in Isolation)**
**Objective:** To verify the correctness of individual, pure functions that do not depend on external services.

*   **Task 2.1: Write Unit Tests for `utils.py`**
    *   **Difficulty:** 4/10
    *   **What:** Create a `tests/test_utils.py` file to test the helper functions.
    *   **Why:** Ensuring these building-block functions work correctly in isolation is crucial for the reliability of the entire system.
    *   **How:** We will write specific `pytest` functions to test `normalize_url`, `extract_text_from_html`, `find_internal_links`, and `process_input_url` with a variety of valid and invalid inputs.

---

## **Phase 3: Integration and End-to-End Testing**
**Objective:** To test how the different components of the scraper work together in a controlled environment.

### **Task 3.1: Write Integration Tests for `page_handler.py` (Overall Difficulty: 6/10)**
This task is broken down into the following sub-tasks:

*   **Sub-task 3.1.1: Test Successful Page Fetch**
    *   **Difficulty:** 4/10
    *   **What:** Test that `fetch_page_content` can successfully retrieve a page from the local test server.
    *   **Why:** To verify the primary success path of our page interaction logic.
    *   **How:** Using `pytest-playwright` and our server fixture, we will call `fetch_page_content` with a valid URL from the test site and assert that it returns the correct HTML content and a 200 status code.

*   **Sub-task 3.1.2: Test 404 Not Found Error Handling**
    *   **Difficulty:** 3/10
    *   **What:** Test how `fetch_page_content` handles a request for a non-existent page.
    *   **Why:** To ensure our error handling is robust and correctly identifies missing pages.
    *   **How:** We will request a URL that does not exist on the local test server and assert that the function returns `None` for the content and the appropriate 404 status code.

*   **Sub-task 3.1.3: Test Page Timeout Handling**
    *   **Difficulty:** 4/10
    *   **What:** Test how `fetch_page_content` behaves when a page takes too long to load.
    *   **Why:** To ensure the scraper can gracefully handle slow or unresponsive websites without hanging indefinitely.
    *   **How:** We will configure the test to simulate a network delay and call `fetch_page_content` with a very short timeout. We will assert that it correctly raises a `PlaywrightTimeoutError` and returns the specific timeout status code (-1).

### **Task 3.2: Write End-to-End Tests for `scraper.py` (Overall Difficulty: 7/10)**
This task is broken down into the following sub-tasks:

*   **Sub-task 3.2.1: Test Basic Successful Crawl**
    *   **Difficulty:** 4/10
    *   **What:** Run a full scrape on the local test site and verify the output.
    *   **Why:** To confirm the entire workflow—from fetching the first page to following links and returning structured data—works as expected.
    *   **How:** We will call `scrape_website` on the `index.html` of our test site. We will then assert that the returned data structure contains the correct number of pages and that the content for each page is accurate.

*   **Sub-task 3.2.2: Test `robots.txt` Disallow Rule**
    *   **Difficulty:** 3/10
    *   **What:** Verify that the scraper does not visit pages disallowed by the `robots.txt` file.
    *   **Why:** To ensure the scraper correctly respects the rules set by website administrators.
    *   **How:** We will run the scraper on the test site and assert that the `disallowed.html` page is not present in the final results.

*   **Sub-task 3.2.3: Test `SCRAPER_MAX_PAGES_PER_DOMAIN` Limit**
    *   **Difficulty:** 3/10
    *   **What:** Confirm that the scraper stops after visiting the maximum number of pages specified in the configuration.
    *   **Why:** To ensure our crawl-limiting safety features are working correctly.
    *   **How:** We will set `SCRAPER_MAX_PAGES_PER_DOMAIN` to a low number (e.g., 2) in the test's `ScraperConfig` and assert that the number of scraped pages in the output does not exceed this limit.

*   **Sub-task 3.2.4: Test DNS Fallback Logic using Mocking**
    *   **Difficulty:** 5/10
    *   **What:** Test the scraper's ability to try alternative domains when a DNS error occurs.
    *   **Why:** To validate one of the scraper's key robustness features without making real, failing network requests.
    *   **How:** Using `pytest-mock`, we will "mock" the underlying network call (`socket.gethostbyname`) to simulate a `socket.gaierror`. We will then run the scraper on a fake domain (e.g., `http://my-company.de`) and assert that it subsequently attempts to scrape the fallback domain (e.g., `http://my-company.com`).

---

## **Phase 4: Finalization and Documentation**
**Objective:** To integrate the tests into the project's workflow and document how to use them.

*   **Task 4.1: Update Documentation**
    *   **Difficulty:** 2/10
    *   **What:** Add a "Testing" section to the `base_scraper/README.md` file.
    *   **Why:** To ensure that anyone working on the project knows that tests exist and how to run them.
    *   **How:** We will add instructions on how to install the development dependencies (`pip install -r requirements-dev.txt`) and how to run the test suite (`pytest`).