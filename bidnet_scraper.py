"""
BidNet Direct Scraper
=====================
Logs in with your credentials, searches for bids by keyword/state,
and extracts both listing data and full bid details into a JSON file.

Requirements:
    pip install playwright beautifulsoup4
    playwright install chromium

Usage:
    python bidnet_scraper.py --email you@example.com --password yourpass \
        --keywords "construction" "IT services" \
        --state "California" \
        --output results.json \
        --max-bids 50
"""

import argparse
import json
import time
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_URL = "https://www.bidnetdirect.com"
LOGIN_URL = f"{BASE_URL}/login"
SEARCH_URL = f"{BASE_URL}/public/supplier/solicitations/statewide"

DEFAULT_DELAY = 1.5   # seconds between requests (be polite)
DEFAULT_MAX   = 25    # max bids to scrape


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def login(page, email: str, password: str) -> bool:
    log(f"Navigating to login page …")
    page.goto(LOGIN_URL, wait_until="networkidle")

    try:
        page.fill('input[name="email"], input[type="email"], #email', email, timeout=8000)
        page.fill('input[name="password"], input[type="password"], #password', password, timeout=8000)
        page.click('button[type="submit"], input[type="submit"], .login-btn', timeout=8000)
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeout:
        log("ERROR: Login form not found or timed out.")
        return False

    # Check if we're still on the login page
    if "/login" in page.url:
        log("ERROR: Login failed — still on login page. Check credentials.")
        return False

    log("Login successful.")
    return True


# ─────────────────────────────────────────────
# SEARCH + LISTING PARSE
# ─────────────────────────────────────────────

def search_bids(page, keyword: str = "", state: str = "", max_bids: int = DEFAULT_MAX) -> list[dict]:
    """
    Navigate search/filter UI and return a list of bid listing dicts.
    Each dict has: title, agency, state, due_date, posted_date, status, url
    """
    log(f"Searching bids — keyword='{keyword}' state='{state}' …")

    # Build URL with query params (BidNet Direct supports these)
    params = []
    if keyword:
        params.append(f"keyword={keyword.replace(' ', '+')}")
    if state:
        params.append(f"state={state.replace(' ', '+')}")
    url = SEARCH_URL + ("?" + "&".join(params) if params else "")

    page.goto(url, wait_until="networkidle")
    time.sleep(DEFAULT_DELAY)

    bids = []
    page_num = 1

    while len(bids) < max_bids:
        log(f"  Parsing listing page {page_num} …")
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # BidNet Direct uses a table or card list for results
        rows = (
            soup.select("table.solicitations-table tbody tr")
            or soup.select(".solicitation-row")
            or soup.select(".bid-listing-item")
            or soup.select("[class*='solicitation']")
        )

        if not rows:
            log("  No bid rows found on this page (selector may need updating).")
            break

        for row in rows:
            if len(bids) >= max_bids:
                break

            link_el = row.select_one("a[href*='/solicitations/']")
            href    = link_el["href"] if link_el else None
            title   = clean(link_el.text) if link_el else clean(row.select_one("td:nth-child(1), .bid-title"))

            cells = row.select("td")
            agency     = clean(cells[1].text) if len(cells) > 1 else ""
            due_date   = clean(cells[2].text) if len(cells) > 2 else ""
            posted     = clean(cells[3].text) if len(cells) > 3 else ""
            status     = clean(cells[4].text) if len(cells) > 4 else ""

            bid = {
                "title":       title,
                "agency":      agency,
                "due_date":    due_date,
                "posted_date": posted,
                "status":      status,
                "url":         BASE_URL + href if href and href.startswith("/") else href,
            }
            bids.append(bid)

        # Paginate
        next_btn = page.query_selector("a[aria-label='Next'], .pagination-next, a:text('Next')")
        if next_btn and len(bids) < max_bids:
            next_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(DEFAULT_DELAY)
            page_num += 1
        else:
            break

    log(f"  Found {len(bids)} listings.")
    return bids


# ─────────────────────────────────────────────
# DETAIL PAGE PARSE
# ─────────────────────────────────────────────

def scrape_detail(page, bid: dict) -> dict:
    """
    Visit a bid's detail page and enrich the bid dict with full details.
    Adds: description, contact_name, contact_email, contact_phone,
          categories, documents (list of {name, url})
    """
    url = bid.get("url")
    if not url:
        return bid

    try:
        page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(DEFAULT_DELAY)
    except PlaywrightTimeout:
        log(f"  TIMEOUT on {url}")
        bid["detail_error"] = "timeout"
        return bid

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    # ── Description ──
    desc_el = (
        soup.select_one(".solicitation-description")
        or soup.select_one(".description-text")
        or soup.select_one("#solicitation-description")
        or soup.select_one("[class*='description']")
    )
    bid["description"] = clean(desc_el.get_text(" ")) if desc_el else ""

    # ── Contact info ──
    contact = {}
    for label_el in soup.select(".contact-label, .field-label, dt"):
        label = clean(label_el.text).lower()
        val_el = label_el.find_next_sibling() or label_el.find_next("dd")
        val = clean(val_el.text) if val_el else ""
        if "name" in label:
            contact["name"] = val
        elif "email" in label:
            contact["email"] = val
        elif "phone" in label:
            contact["phone"] = val

    # Also try mailto / tel links
    if not contact.get("email"):
        mailto = soup.select_one("a[href^='mailto:']")
        if mailto:
            contact["email"] = mailto["href"].replace("mailto:", "").strip()
    if not contact.get("phone"):
        tel = soup.select_one("a[href^='tel:']")
        if tel:
            contact["phone"] = tel["href"].replace("tel:", "").strip()

    bid["contact"] = contact

    # ── Categories / NIGP / NAICS ──
    categories = []
    for el in soup.select(".category-item, .nigp-code, .naics-code, [class*='category']"):
        t = clean(el.text)
        if t:
            categories.append(t)
    bid["categories"] = list(dict.fromkeys(categories))  # dedupe

    # ── Documents ──
    documents = []
    for a in soup.select("a[href*='/documents/'], a[href$='.pdf'], a[href*='download']"):
        name = clean(a.text) or "document"
        href = a.get("href", "")
        full = BASE_URL + href if href.startswith("/") else href
        if full:
            documents.append({"name": name, "url": full})
    bid["documents"] = documents

    return bid


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run(email: str, password: str, keywords: list[str], state: str,
        output: str, max_bids: int, headless: bool):

    all_bids: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # ── Login ──
        if not login(page, email, password):
            browser.close()
            sys.exit(1)

        # ── Search for each keyword ──
        seen_urls: set[str] = set()

        for kw in (keywords or [""]):
            listings = search_bids(page, keyword=kw, state=state, max_bids=max_bids)

            for bid in listings:
                url = bid.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                log(f"Fetching detail: {bid.get('title', url)[:70]} …")
                enriched = scrape_detail(page, bid)
                enriched["scraped_at"] = datetime.utcnow().isoformat() + "Z"
                enriched["search_keyword"] = kw
                all_bids.append(enriched)

        browser.close()

    # ── Save ──
    out_path = Path(output)
    out_path.write_text(
        json.dumps(all_bids, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    log(f"Saved {len(all_bids)} bids → {out_path.resolve()}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BidNet Direct scraper")

    parser.add_argument("--email",    required=True,  help="BidNet Direct account email")
    parser.add_argument("--password", required=True,  help="BidNet Direct account password")
    parser.add_argument("--keywords", nargs="*",      default=[""],
                        help="Search keywords (space-separated, quote multi-word terms)")
    parser.add_argument("--state",    default="",     help="Filter by state name, e.g. 'California'")
    parser.add_argument("--output",   default="bidnet_results.json", help="Output JSON filename")
    parser.add_argument("--max-bids", type=int, default=DEFAULT_MAX,
                        help=f"Max bids to scrape per keyword (default: {DEFAULT_MAX})")
    parser.add_argument("--no-headless", action="store_true",
                        help="Show browser window (useful for debugging)")

    args = parser.parse_args()

    run(
        email=args.email,
        password=args.password,
        keywords=args.keywords,
        state=args.state,
        output=args.output,
        max_bids=args.max_bids,
        headless=not args.no_headless,
    )