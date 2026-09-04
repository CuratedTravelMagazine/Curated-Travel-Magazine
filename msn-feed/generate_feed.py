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
    # rss2json returns dates like "2026-09-03 08:58:40"
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def build_item(item, config):
    title = (item.get("title") or "").strip()
    url = item.get("link") or ""
    guid = item.get("guid") or url

    pub_date_raw = item.get("pubDate")
    pub_date = rfc822(pub_date_raw) if pub_date_raw else ""

    raw_html = item.get("content") or item.get("description") or ""
    cleaned_html = clean_html(raw_html)

    thumbnail_url = item.get("thumbnail")
    if not thumbnail_url:
        enclosure = item.get("enclosure") or {}
        thumbnail_url = enclosure.get("link") or enclosure.get("url")
    if not thumbnail_url:
        thumbnail_url = config["logo_square"]

    categories = item.get("categories") or config["default_categories"]

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

    # Pull directly from Substack RSS (10 items instead of 4)
feed = feedparser.parse("https://curatedtravelmagazine.substack.com/feed")

items = []
for entry in feed.entries[:10]:  # You can increase this number if you want
    item = {
        "title": entry.title,
        "link": entry.link,
        "guid": entry.id,
        "pubDate": entry.published if hasattr(entry, "published") else "",
        "content": entry.content[0].value if hasattr(entry, "content") else entry.summary,
        "thumbnail": None,
        "categories": [tag.term for tag in entry.tags] if hasattr(entry, "tags") else []
    }
    items.append(item)


    items_xml = [build_item(item, config) for item in items]

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
