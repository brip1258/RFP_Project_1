import os
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_URL = "https://subscribers.cip-info.com/"
REPORT_URL = urljoin(BASE_URL, "queryReport.do")

load_dotenv()


def get_session() -> requests.Session:
    """Log in to subscribers.cip-info.com and return an authenticated session."""
    username = os.environ.get("CIP_USERNAME")
    password = os.environ.get("CIP_PASSWORD")
    if not username or not password:
        sys.exit(
            "Missing CIP_USERNAME / CIP_PASSWORD. Copy .env.example to .env "
            "and fill in your credentials."
        )

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; cip-scraper/1.0)"})

    # Hitting the protected report URL while unauthenticated redirects to login.jsp
    login_page = session.get(REPORT_URL)
    soup = BeautifulSoup(login_page.text, "lxml")
    form = soup.find("form", id="loginForm")
    if form is None:
        sys.exit(
            "Could not find login form — site markup may have changed. "
            "Check debug output."
        )

    action = urljoin(login_page.url, form.get("action", "auth/"))

    payload = {"j_username": username, "j_password": password, "j_uri": ""}
    submit_name = form.find("input", {"type": "submit"})
    if submit_name and submit_name.get("name"):
        payload[submit_name["name"]] = submit_name.get("value", "Login")

    resp = session.post(action, data=payload)

    if "j_password" in resp.text:
        sys.exit("Login failed — check your CIP_USERNAME / CIP_PASSWORD in .env")

    return session


if __name__ == "__main__":
    session = get_session()
    print("Login succeeded.")
    print("Landed on:", session.get(REPORT_URL).url)
