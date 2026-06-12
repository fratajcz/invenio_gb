"""
Fetch records from InvenioRDM API and transform them into the target submission format.
"""

import json
import requests
import urllib3

# Suppress SSL warnings for self-signed certs (localhost dev environment)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://127.0.0.1:5000/api/records"

FILE_NAME = "new_records.json"

# Optional: set a Bearer token if authentication is required
API_TOKEN = "GVilIY1rjbZSMvf3OFFCtp1IKVzsvM0cDi0tbWYcjWsVI1UMdGpC2XshIHhA"  # e.g. "your-token-here"


def fetch_records(url: str) -> list[dict]:
    """Send GET request to the records API and return the list of hits."""
    headers = {}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    print(f"Fetched {len(hits)} record(s).")
    return hits


def transform_record(record: dict) -> dict:
    """Transform a single InvenioRDM record into the target submission format."""
    metadata = record.get("metadata", {})
    access = record.get("access", {})
    files = record.get("files", {})
    custom = record.get("custom_fields", {})

    # --- Access ---
    transformed_access = {
        "record": access.get("record", "public"),
        "files": access.get("files", "public"),
    }

    # --- Files ---
    transformed_files = {
        "enabled": files.get("enabled", True),
    }

    # --- Creators ---
    raw_creators = metadata.get("creators", [])
    transformed_creators = []
    for creator in raw_creators:
        person_or_org = creator.get("person_or_org", {})

        transformed_creator = {
            "person_or_org": {
                "family_name": person_or_org.get("family_name", ""),
                "given_name": person_or_org.get("given_name", ""),
                "identifiers": person_or_org.get("identifiers", []),
                "name": person_or_org.get("name", ""),
                "type": person_or_org.get("type", "personal"),
            }
        }

        # Include affiliations only if present
        if creator.get("affiliations"):
            transformed_creator["affiliations"] = creator["affiliations"]

        # Include role only if present
        if creator.get("role"):
            transformed_creator["role"] = creator["role"]

        transformed_creators.append(transformed_creator)

    # --- Resource type: flatten to just the id ---
    resource_type_raw = metadata.get("resource_type", {})
    resource_type = {"id": resource_type_raw.get("id", "")}

    # --- Assemble final structure ---
    transformed = {
        "access": transformed_access,
        "files": transformed_files,
        "metadata": {
            "creators": transformed_creators,
            "publication_date": metadata.get("publication_date", ""),
            "publisher": metadata.get("publisher", ""),
            "resource_type": resource_type,
            "title": metadata.get("title", ""),
        },
        "type": "community-submission",
        "custom_fields": custom,
    }

    return transformed


def main():
    hits = fetch_records(API_URL)

    transformed_records = [transform_record(hit) for hit in hits]

    output = json.dumps(transformed_records, indent=2, ensure_ascii=False)
    print("\nTransformed records:\n")
    print(output)

    # Optionally write to file
    output_path = FILE_NAME
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
