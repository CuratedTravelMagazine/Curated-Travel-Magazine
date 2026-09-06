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

def build_item(entry, config):
    title = entry.get("title", "").strip()
    url = entry.get("link", "")
    guid = entry.get("guid", url)

    pub_date_raw = entry.get("pubDate")
    pub_date = rfc822(pub_date_raw) if pub_date_raw else ""

    raw_html = entry.get("content") or entry.get("description") or ""
    cleaned_html = clean_html(raw_html)

    thumbnail_url = entry.get("thumbnail")
    categories = entry.get("categories", config["default_categories"])

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

    print("DEBUG: Fetching RSS feed via rss2json…")
    resp = requests.get(config["substack_api_url"])
    data = resp.json()

    print("DEBUG: API keys:", list(data.keys()))
    items = data.get("items", [])

    print("DEBUG: Number of posts:", len(items))
    if not items:
        print("DEBUG: No posts found — exiting without writing feed.")
        return

    parsed_items = []
    for entry in items:
        parsed_items.append(build_item(entry, config))

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
