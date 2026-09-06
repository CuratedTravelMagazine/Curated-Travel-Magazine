import os
import json
import requests
from datetime import datetime
from clean_html import clean_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config(path=None):
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def rfc822(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return ""

def fetch_substack_api(url):
    print("DEBUG: Fetching Substack API…")

    # Full browser headers to bypass Substack bot protection
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://curatedtravelmagazine.substack.com/",
        "Origin": "https://curatedtravelmagazine.substack.com",
        "Connection": "keep-alive"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        print("DEBUG: Status code:", resp.status_code)
        print("DEBUG: Raw response (first 200 chars):", resp.text[:200])

        if resp.status_code != 200:
            print("DEBUG: Non-200 response, aborting API parse.")
            return None

        # Attempt JSON decode
        try:
            return resp.json()
        except Exception as e:
            print("DEBUG: JSON decode failed:", e)
            return None

    except Exception as e:
        print("DEBUG: API request failed:", e)
        return None

def build_item(entry, config):
    title = entry.get("title", "").strip()
    url = entry.get("canonical_url", "")
    guid = entry.get("id", url)

    pub_date_raw = entry.get("post_date")
    pub_date = rfc822(pub_date_raw) if pub_date_raw else ""

    raw_html = entry.get("body_html", "")
    cleaned_html = clean_html(raw_html)

    thumbnail_url = None
    if entry.get("cover_image"):
        thumbnail_url = entry["cover_image"].get("url")

    categories = entry.get("tags", config["default_categories"])

    item_xml = []
    item_xml.append("<item>")
    item_xml.append(f"  <title>{title}</title>")
    item_xml.append(f"  <link>{url}</link>")
    item_xml.append(f"  <guid>{guid
