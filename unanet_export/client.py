"""Minimal REST client for the Unanet API.

Configure via environment variables (see .env):
    UNANET_BASE_URL     e.g. https://yourcompany.unanet.biz
    UNANET_API_KEY      API key/token generated in Unanet
    UNANET_AUTH_HEADER  Header name for the key (default: Authorization)
    UNANET_AUTH_SCHEME  Prefix before the key, e.g. "Bearer" (default: Bearer)
    UNANET_LEADS_ENDPOINT  Path to the leads list endpoint (default: /api/leads)

The exact auth scheme and endpoint path vary by Unanet instance/version --
check your instance's API docs (usually under Admin > API, or a Swagger UI)
and adjust the env vars above if requests come back 401/404.
"""
import os
import sys
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("UNANET_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("UNANET_API_KEY")
AUTH_HEADER = os.environ.get("UNANET_AUTH_HEADER", "Authorization")
AUTH_SCHEME = os.environ.get("UNANET_AUTH_SCHEME", "Bearer")
LEADS_ENDPOINT = os.environ.get("UNANET_LEADS_ENDPOINT", "/api/leads")


def get_session() -> requests.Session:
    """Build a requests session authenticated against the Unanet API."""
    if not BASE_URL or not API_KEY:
        sys.exit(
            "Missing UNANET_BASE_URL / UNANET_API_KEY. Fill in unanet_export/.env "
            "with your Unanet instance URL and API key."
        )

    session = requests.Session()
    header_value = f"{AUTH_SCHEME} {API_KEY}".strip() if AUTH_SCHEME else API_KEY
    session.headers.update({AUTH_HEADER: header_value, "Accept": "application/json"})
    return session


def fetch_all(session: requests.Session, endpoint: str = None, page_size: int = 100) -> list:
    """Page through a Unanet list endpoint and return every record.

    Tries `page`/`pageSize` query params and unwraps common list envelopes
    (a bare list, or an object with a "data"/"items"/"results" key).
    """
    url = urljoin(BASE_URL + "/", (endpoint or LEADS_ENDPOINT).lstrip("/"))
    records = []
    page = 1

    while True:
        resp = session.get(url, params={"page": page, "pageSize": page_size})
        resp.raise_for_status()
        batch = _extract_records(resp.json())
        if not batch:
            break

        records.extend(batch)
        print(f"  page {page}: +{len(batch)} records ({len(records)} total)")
        if len(batch) < page_size:
            break
        page += 1

    return records


def _extract_records(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "records", "leads"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []
