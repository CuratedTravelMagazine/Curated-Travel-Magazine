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
    # Substack API usually returns ISO timestamps; adjust if needed
    # Example: "2026-09-03T08:58:40.000Z"
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def build_item(post, config):
    title = post.get("title", "").strip()
    url = post.get("canonical_url") or post.get("url")
    guid = url

    published_at = post.get("published_at") or post.get("created_at")
    pub_date = rfc822(published_at) if published_at else ""

    # Get HTML body from API (field name may be 'body_html' or 'body')
    raw_html = post.get("body_html") or post.get("body") or ""
    cleaned_html = clean_html(raw_html)

    # Thumbnail: use first image from post if available
    thumbnail_url = None
    images = post.get("images") or []
    if images:
        # Assume images is a list of dicts with 'url' or similar
        thumbnail_url = images[0].get("url")
    if not thumbnail_url:
        # Fallback to logo if no image
        thumbnail_url = config["logo_square"]

    # Categories: use tags if present, else defaults
    tags = post.get("tags") or []
    if tags:
        categories = [t.get("name", "").strip() for t in tags if t.get("name")]
    else:
        categories = config["default_categories"]

    # Build XML for this item
    item_xml = []
    item_xml.append("    <item>")
    item_xml.append(f"        <title><![CDATA[{title}]]></title>")
    item_xml.append(f"        <link>{url}</link>")
    item_xml.append(f"        <guid isPermaLink=\"false\">{guid}</guid>")
    item_xml.append(f"        <dc:creator><![CDATA[{config['author_name']}]]></dc:creator>")
    if pub_date:
        item_xml.append(f"        <pubDate>{pub_date}</pubDate>")
    for cat in categories:
        item_xml.append(f"        <category><![CDATA[{cat}]]></category>")
    item_xml.append(f"        <media:thumbnail url=\"{thumbnail_url}\" />")
    item_xml.append("        <content:encoded><![CDATA[")
    item_xml.append(cleaned_html)
    item_xml.append("        ]]></content:encoded>")
    item_xml.append("    </item>")

    return "\n".join(item_xml)


def main():
    config = load_config()

    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
resp = requests.get(config["substack_api_url"], headers=headers)
    resp.raise_for_status()
    data = resp.json()

    posts = data if isinstance(data, list) else data.get("posts", [])

    items_xml = []
    for post in posts:
        items_xml.append(build_item(post, config))

    # Build full feed
    feed_xml = []
    feed_xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    feed_xml.append('<rss version="2.0"')
    feed_xml.append('    xmlns:content="http://purl.org/rss/1.0/modules/content/"')
    feed_xml.append('    xmlns:dc="http://purl.org/dc/elements/1.1/"')
    feed_xml.append('    xmlns:media="http://search.yahoo.com/mrss/"')
    feed_xml.append('>')
    feed_xml.append("<channel>")
    feed_xml.append(f"    <title>{config['site_title']}</title>")
    feed_xml.append(f"    <link>{config['site_link']}</link>")
    feed_xml.append(f"    <description>{config['site_description']}</description>")
    feed_xml.append(f"    <language>{config['language']}</language>")
    feed_xml.append("    <image>")
    feed_xml.append(f"        <url>{config['logo_square']}</url>")
    feed_xml.append(f"        <title>{config['site_title']}</title>")
    feed_xml.append(f"        <link>{config['site_link']}</link>")
    feed_xml.append("    </image>")
    feed_xml.append("\n".join(items_xml))
    feed_xml.append("</channel>")
    feed_xml.append("</rss>")

    output_path = os.path.join(SCRIPT_DIR, config["output_file"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feed_xml))

    print(f"Feed written to {output_path}")


if __name__ == "__main__":
    main()
