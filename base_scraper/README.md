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