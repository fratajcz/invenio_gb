"""
Load transformed records from file and POST them one by one to the InvenioRDM API.
"""

import json
import time
import requests
import urllib3
from tqdm import tqdm

# Suppress SSL warnings for self-signed certs (localhost dev environment)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RECORDS_API_URL = "https://127.0.0.1:5000/api/records"
REVIEW_API_URL = "https://127.0.0.1:5000/api/records/{}/draft/review"
SUBMIT_REVIEW_API_URL = "https://127.0.0.1:5000/api/records/{}/draft/actions/submit-review"
INPUT_FILE = "records.json"

# catchall community id

COMMUNITY_ID = "701e62f1-0854-45b7-a2f9-10b783bb3c3e"

# Optional: set a Bearer token if authentication is required
API_TOKEN = "GVilIY1rjbZSMvf3OFFCtp1IKVzsvM0cDi0tbWYcjWsVI1UMdGpC2XshIHhA"  # e.g. "your-token-here"

# Delay in seconds between requests (set to 0 to disable)
REQUEST_DELAY = 0.5


def load_records(filepath: str) -> list[dict]:
    """Load transformed records from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} record(s) from '{filepath}'.")
    return records


def post_record(record: dict, index: int, api_url, method="post") -> dict | None:
    """POST a single record to the API. Returns the response JSON or None on failure."""
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    try:
        method_callable = getattr(requests, method.lower())
        response = method_callable(
            api_url,
            headers=headers,
            json=record,
            verify=False,
        )

        if response.ok:
            print(f"[{index}] ✓ {"Posted" if method.lower() == "post" else "Put"} successfully (HTTP {response.status_code})")
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

    draft_ids = []

    print(f"\nPosting drafts...")
    for i, record in tqdm(enumerate(records, start=1)):
        
        result = post_record(record, i, RECORDS_API_URL)

        if result is not None:
            succeeded += 1
            draft_ids.append(result["id"])
            results.append({"status": "success", "index": i, "response": result})
        else:
            failed += 1
            results.append({"status": "failed", "index": i, "record": record})

        if REQUEST_DELAY > 0 and i < len(records):
            time.sleep(REQUEST_DELAY)

    # Summary
    print(f"\n{'='*40}")
    print(f"Done. {succeeded} succeeded, {failed} failed out of {len(records)} drafts(s).")

    # Save results log
    log_path = "post_results.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results log saved to '{log_path}'.")

    print(f"\n{'*'*40}")
    print(f"Attaching drafts to community {COMMUNITY_ID}")

    message = {
        "receiver":{
            "community": "{}".format(COMMUNITY_ID)
        },
        "type": "community-submission"
    }

    print(f"\nAttaching Communities to drafts...")
    for i, draft_id in tqdm(enumerate(draft_ids, start=1)):
        

        result = post_record(message, i, REVIEW_API_URL.format(draft_id), method="put")

    message = {
        "payload":{
            "content": "automated review submission",
            "format": "html"
            },
    }

    print(f"\nSubmitting Reviews to Community and accepting them...")
    for i, draft_id in tqdm(enumerate(draft_ids, start=1)):
        result = post_record(message, i, SUBMIT_REVIEW_API_URL.format(draft_id), method="post")
        accept_url = result["links"]["actions"]["accept"]
        result = post_record(None, i, accept_url, method="post")


if __name__ == "__main__":
    main()
