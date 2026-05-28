"""
Load transformed records from file and POST them one by one to the InvenioRDM API.
"""

import json
import time
import requests
import urllib3

# Suppress SSL warnings for self-signed certs (localhost dev environment)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://127.0.0.1:400/api/records"
INPUT_FILE = "transformed_records.json"

# Optional: set a Bearer token if authentication is required
API_TOKEN = None  # e.g. "your-token-here"

# Delay in seconds between requests (set to 0 to disable)
REQUEST_DELAY = 0.5


def load_records(filepath: str) -> list[dict]:
    """Load transformed records from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} record(s) from '{filepath}'.")
    return records


def post_record(record: dict, index: int) -> dict | None:
    """POST a single record to the API. Returns the response JSON or None on failure."""
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=record,
            verify=False,
        )

        if response.ok:
            print(f"[{index}] ✓ Posted successfully (HTTP {response.status_code})")
            return response.json()
        else:
            print(f"[{index}] ✗ Failed (HTTP {response.status_code}): {response.text}")
            return None

    except requests.exceptions.ConnectionError as e:
        print(f"[{index}] ✗ Connection error: {e}")
        return None
    except requests.exceptions.Timeout:
        print(f"[{index}] ✗ Request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[{index}] ✗ Unexpected error: {e}")
        return None


def main():
    records = load_records(INPUT_FILE)

    results = []
    succeeded = 0
    failed = 0

    for i, record in enumerate(records, start=1):
        print(f"\nPosting record {i}/{len(records)}...")
        result = post_record(record, i)

        if result is not None:
            succeeded += 1
            results.append({"status": "success", "index": i, "response": result})
        else:
            failed += 1
            results.append({"status": "failed", "index": i, "record": record})

        if REQUEST_DELAY > 0 and i < len(records):
            time.sleep(REQUEST_DELAY)

    # Summary
    print(f"\n{'='*40}")
    print(f"Done. {succeeded} succeeded, {failed} failed out of {len(records)} record(s).")

    # Save results log
    log_path = "post_results.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results log saved to '{log_path}'.")


if __name__ == "__main__":
    main()
