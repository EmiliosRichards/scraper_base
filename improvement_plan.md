# Base Scraper Module: Improvement Plan

This document outlines the action plan for improving the `base_scraper` module based on a comprehensive audit.

---

## 1. Unify and Enhance URL Processing Logic

*   **What:** The `scrape_website` function currently uses a basic DNS fallback mechanism and simple URL normalization. A much more robust function, `process_input_url`, already exists in `utils.py` but is not being used. This task is to replace the current logic with the superior, existing function.
*   **Why:** Using `process_input_url` will make the scraper more resilient to malformed input URLs and improve the success rate of the DNS fallback by checking a wider range of TLDs, as defined in the configuration. This avoids code duplication and centralizes URL processing.
*   **How:**
    1.  Modify the `scrape_website` function in `scraper.py`.
    2.  Remove the existing `tldextract`-based fallback logic.
    3.  Call `process_input_url` from `utils.py` at the beginning of the function to process the `given_url`.
    4.  The `process_input_url` function already handles TLD probing, so the loop over `entry_candidates` can be simplified or removed.
*   **Difficulty:** Medium

---

## 2. Optimize Link Handling Performance

*   **What:** The current implementation has two performance bottlenecks: sorting the URL queue on every iteration and pre-validating every discovered link with a `HEAD` request.
*   **Why:** For websites with many links, these operations can significantly slow down the scraping process. Using a more efficient data structure and removing the pre-validation step will make the scraper faster and more efficient.
*   **How:**
    1.  **Replace List with Priority Queue:** In `_perform_scrape_for_entry_point` (`scraper.py`), replace the `urls_to_scrape_q` list with a priority queue (using Python's `heapq` module). This will make dequeuing the highest-priority URL much more efficient.
    2.  **Remove Pre-emptive Link Validation:** In `_perform_scrape_for_entry_point` (`scraper.py`), remove the call to `validate_link_status` before adding a link to the queue. The existing error handling within `fetch_page_content` is sufficient to handle broken links when they are actually visited.
*   **Difficulty:** Medium

---

## 3. Refine Link Scoring Algorithm

*   **What:** The link scoring logic in `find_internal_links` (`utils.py`) is complex and could be simplified for better clarity and maintenance. The scoring tiers have some overlap and could be made more distinct.
*   **Why:** A clearer algorithm is easier to debug and adapt. Simplifying the scoring logic will make the scraper's behavior more predictable.
*   **How:**
    1.  Review the scoring tiers in `find_internal_links`.
    2.  Consolidate overlapping keyword checks.
    3.  Refactor the nested `if score < ...` blocks into a more linear, readable structure.
    4.  Ensure the penalties for path depth are applied consistently.
*   **Difficulty:** Low

---

## 4. Improve Logging and Code Cleanup

*   **What:** There are minor issues in the codebase, such as debug messages logged at the `INFO` level.
*   **Why:** Consistent and clean logging is crucial for debugging and monitoring.
*   **How:**
    1.  In `utils.py`, change the `logger.info` calls that start with "DEBUG PATH" in `get_safe_filename` to `logger.debug`.
    2.  Perform a general review of the codebase for any other similar inconsistencies.
*   **Difficulty:** Low