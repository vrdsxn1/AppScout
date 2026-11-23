"""Small connection check for the Firecrawl scrape API.

Run from the project root with:
    .\\.venv\\Scripts\\python.exe scripts\\test_firecrawl.py
"""

import os
import sys

import requests
from dotenv import load_dotenv


API_URL = "https://api.firecrawl.dev/v2/scrape"
TEST_URL = "https://docs.firecrawl.dev/"
REQUEST_TIMEOUT = (10, 60)  # connect timeout, read timeout (seconds)


def main() -> int:
    load_dotenv()
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        print("Error: FIRECRAWL_API_KEY is missing or blank. Add it to the project .env file.")
        return 1

    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": TEST_URL, "formats": ["markdown"]},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        print("Error: Firecrawl request timed out.")
        return 1
    except requests.ConnectionError:
        print("Error: Could not connect to Firecrawl. Check your network connection.")
        return 1
    except requests.RequestException:
        print("Error: Firecrawl request failed before a response was received.")
        return 1

    if not response.ok:
        print(f"Error: Firecrawl returned HTTP {response.status_code} ({response.reason}).")
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("Error: Firecrawl returned a successful HTTP status but invalid JSON.")
        return 1

    if not isinstance(payload, dict) or payload.get("success") is not True:
        print("Error: Firecrawl response was missing a successful scrape result.")
        return 1

    data = payload.get("data")
    if not isinstance(data, dict):
        print("Error: Firecrawl response did not contain a valid data object.")
        return 1
    if not isinstance(data.get("markdown"), str):
        print("Error: Firecrawl response did not contain the requested scraped markdown.")
        return 1

    metadata = data.get("metadata")
    title = metadata.get("title") if isinstance(metadata, dict) else None
    if isinstance(title, str) and title.strip():
        print("Firecrawl connection successful.")
        print(f"Scraped page title: {title.strip()}")
    else:
        print("Firecrawl connection successful. No page title was returned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
