"""Pull all leads from Unanet and save the ones with a CIP reference as JSON.

A lead "has a CIP reference" if the word CIP appears anywhere in its fields
(description, notes, comments, etc.) -- the search checks every text field
on the record, not just one, since field names vary by Unanet configuration.

Usage: python export_cip_leads.py
"""
import json
import os
import re
from datetime import datetime, timezone

from client import BASE_URL, fetch_all, get_session

OUTPUT_JSON_PATH = os.path.join(os.path.dirname(__file__), "output", "unanet_cip_leads.json")

CIP_PATTERN = re.compile(r"\bCIP\b", re.IGNORECASE)


def _contains_cip_reference(value) -> bool:
    if isinstance(value, str):
        return bool(CIP_PATTERN.search(value))
    if isinstance(value, dict):
        return any(_contains_cip_reference(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_cip_reference(v) for v in value)
    return False


def main():
    print(f"Connecting to Unanet at {BASE_URL}...")
    session = get_session()

    print("Fetching leads...")
    leads = fetch_all(session)
    print(f"Fetched {len(leads)} leads total.")

    print("Scanning leads for CIP references...")
    matches = [lead for lead in leads if _contains_cip_reference(lead)]
    print(f"Found {len(matches)} leads with a CIP reference.")

    output = {
        "source": BASE_URL,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "totalLeadsScanned": len(leads),
        "matchCount": len(matches),
        "leads": matches,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved JSON to {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
