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

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CuratedTravelBot/1.0; +https://www.curatedtravelmagazine.com)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        print("DEBUG: Status code:", resp.status_code)
        print("DEBUG: Raw response (first 200 chars):", resp.text[:200])

        if resp.status_code != 200:
            print("DEBUG: Non-200 response, aborting API parse.")
            return None

        return resp.json()

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

def main():
    config = load_config()
    print("DEBUG: Loaded config:", config)

    # Fetch Substack API
    data = fetch_substack_api(config["substack_api_url"])

    if not data:
        print("DEBUG: Substack API returned no data. Exiting.")
        return

    posts = data.get("posts") or data.get("items") or []
    print("DEBUG: Number of posts:", len(posts))

    if not posts:
        print("DEBUG: No posts found — exiting without writing feed.")
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
