import os
import json
import requests
import feedparser
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

# ---------------------------------------------------------
# 1. Substack API fetch (with full browser headers)
# ---------------------------------------------------------
def fetch_substack_api(url):
    print("DEBUG: Fetching Substack API…")

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

        try:
            return resp.json()
        except Exception as e:
            print("DEBUG: JSON decode failed:", e)
            return None

    except Exception as e:
        print("DEBUG: API request failed:", e)
        return None

# ---------------------------------------------------------
# 2. RSS fallback (always works even if API blocks)
# ---------------------------------------------------------
def fetch_rss_fallback():
    print("DEBUG: Using RSS fallback…")

    rss_url = "https://curatedtravelmagazine.substack.com/feed"
    feed = feedparser.parse(rss_url)

    print("DEBUG: RSS entries:", len(feed.entries))

    posts = []
    for entry in feed.entries:
        item = {
            "title": entry.title,
            "canonical_url": entry.link,
            "id": entry.id,
            "post_date": entry.published if hasattr(entry, "published") else "",
            "body_html": entry.content[0].value if hasattr(entry, "content") else entry.summary,
            "cover_image": None,
            "tags": [tag.term for tag in entry.tags] if hasattr(entry, "tags") else []
        }
        posts.append(item)

    return posts

# ---------------------------------------------------------
# 3. Build MSN XML item
# ---------------------------------------------------------
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
    item_xml.append(f"  <guid>{guid}</guid>")
    item_xml.append(f"  <dc:creator>{config['author_name']}</dc:creator>")

    if pub_date:
        item_xml.append(f"  <pubDate>{pub_date}</pubDate>")

    for cat in categories:
        item_xml.append(f"  <category>{cat}</category>")

    if thumbnail_url:
        item_xml.append(f'  <media:thumbnail url="{thumbnail_url}" />')

    item_xml.append("  <content:encoded><![CDATA[")
    item_xml.append(cleaned_html)
    item_xml.append("  ]]></content:encoded>")
    item_xml.append("</item>")

    return "\n".join(item_xml)

# ---------------------------------------------------------
# 4. Main feed generator
# ---------------------------------------------------------
def main():
    config = load_config()
    print("DEBUG: Loaded config:", config)

    # Try Substack API first
    data = fetch_substack_api(config["substack_api_url"])

    posts = []
    if data and isinstance(data, dict) and data.get("posts"):
        posts = data["posts"]
        print("DEBUG: Substack API returned posts:", len(posts))
    else:
        print("DEBUG: Substack API failed or returned no posts.")
        posts = fetch_rss_fallback()

    if not posts:
        print("DEBUG: No posts found from API or RSS. Exiting.")
        return

    parsed_items = [build_item(entry, config) for entry in posts]

    feed_xml = []
    feed_xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    feed_xml.append('<rss version="2.0"')
    feed_xml.append(' xmlns:content="http://purl.org/rss/1.0/modules/content/"')
    feed_xml.append(' xmlns:dc="http://purl.org/dc/elements/1.1/"')
    feed_xml.append(' xmlns:media="http://search.yahoo.com/mrss/">')
    feed_xml.append('>')
    feed_xml.append('<channel>')
    feed_xml.append(f'  <title>{config["site_title"]}</title>')
    feed_xml.append(f'  <link>{config["site_link"]}</link>')
    feed_xml.append(f'  <description>{config["site_description"]}</description>')
    feed_xml.append(f'  <language>{config["language"]}</language>')
    feed_xml.append(f'  <image><url>{config["logo_square"]}</url></image>')
    feed_xml.append("\n".join(parsed_items))
    feed_xml.append('</channel>')
    feed_xml.append('</rss>')

    output_path = os.path.join(SCRIPT_DIR, config["output_file"])
    print("DEBUG: Writing feed to:", output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feed_xml))

    print("DEBUG: File exists:", os.path.exists(output_path))
    print("DEBUG: Feed generation complete.")

if __name__ == "__main__":
    main()
