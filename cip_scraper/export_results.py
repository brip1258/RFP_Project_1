"""Log in, run the Colorado / Architectural-Structural search, and export all
matching CIP project records as JSON.

Usage: python export_results.py
"""
import json
import os
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from tqdm import tqdm

from auth import REPORT_URL, get_session

from pymongo import MongoClient
from pymongo.server_api import ServerApi


DEBUG_HTML_PATH = os.path.join(os.path.dirname(__file__), "debug", "queryResults_co_arch.html")
OUTPUT_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "output", "colorado_architectural_structural.json"
)

SEARCH_PAYLOAD = {
    "from": "ReportAction.query",
    "objectId": "",
    "marketNames": "Colorado",
    "categoryNames": "Architectural/structural",
    "agency": "",
    "reportNumberSearchCriteria": "",
    "projectName": "",
    "projectYear": "",
    "overallBudgetMin": "",
    "overallBudgetMax": "",
    "profServicesBudgetMin": "",
    "profServicesBudgetMax": "",
    "revisionDateSearchCriteria": "after",
    "revisionDate": "",
    "revisionDateUpperBound": "",
    "action": "Search",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_record_table(table) -> bool:
    return "ID Number" in table.get_text()


def parse_record(table) -> dict:
    record = {}

    rowspan_td = table.find("td", attrs={"rowspan": True})
    description = _norm(rowspan_td.get_text(" ", strip=True)) if rowspan_td else ""

    trs = table.find_all("tr")
    skip_next = False
    for idx, tr in enumerate(trs):
        if skip_next:
            skip_next = False
            continue

        tds = tr.find_all("td")
        first_b = tds[0].find("b") if tds else None

        # The Contact/Phone/Revised/Email block is laid out across two rows
        # with the Revised date right-aligned under its own label, not next
        # to it — handle it as a unit instead of a simple label/value walk.
        if first_b and first_b.get_text(strip=True).rstrip(":") == "Contact":
            next_tds = trs[idx + 1].find_all("td") if idx + 1 < len(trs) else []
            record["Contact"] = _norm(tds[1].get_text(" ", strip=True)) if len(tds) > 1 else ""
            record["Phone"] = _norm(tds[3].get_text(" ", strip=True)) if len(tds) > 3 else ""
            record["Email"] = (
                _norm(next_tds[3].get_text(" ", strip=True)) if len(next_tds) > 3 else ""
            )
            record["Revised"] = (
                _norm(next_tds[-1].get_text(" ", strip=True)) if next_tds else ""
            )
            skip_next = True
            continue

        i = 0
        while i < len(tds):
            b = tds[i].find("b")
            if b:
                label = _norm(b.get_text(strip=True)).rstrip(":").strip()
                value_td = tds[i + 1] if i + 1 < len(tds) else None
                value = _norm(value_td.get_text(" ", strip=True)) if value_td is not None else ""
                record[label] = description if label == "Description" else value
                i += 2
            else:
                i += 1

    return record


def main():
    print("[1/5] Logging in...")
    session = get_session()

    print("[2/5] Submitting search (Colorado / Architectural-Structural)...")
    resp = session.post(REPORT_URL, data=SEARCH_PAYLOAD)

    print("[3/5] Saving raw response to debug/...")
    os.makedirs(os.path.dirname(DEBUG_HTML_PATH), exist_ok=True)
    with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(resp.text)

    print("[4/5] Parsing project records...")
    soup = BeautifulSoup(resp.text, "lxml")
    tables = [t for t in soup.find_all("table") if _is_record_table(t)]
    records = [parse_record(t) for t in tqdm(tables, unit="record")]

    output = {
        "source": REPORT_URL,
        "filters": {
            "marketNames": SEARCH_PAYLOAD["marketNames"],
            "categoryNames": SEARCH_PAYLOAD["categoryNames"],
        },
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "recordCount": len(records),
        "records": records,
    }

    print("[5/5] Writing JSON output...")
    try:
        username = os.environ.get("MONG_USERNAME")
        password = os.environ.get("MONG_PASSWORD")
        uri = f"mongodb+srv://{username}:{password}@crpupdates.7pf961t.mongodb.net/?appName=crpUpdates"
        client= MongoClient(uri, server_api=ServerApi('1')) 
        db = client["crpUpdates"]
        collection = db["crpUpdates"]
        collection.insert_many(output['records'])
    except:
        print("Couldn't upload to database")
    print(f"Done — parsed {len(records)} records")
    print(f"Saved JSON to {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
