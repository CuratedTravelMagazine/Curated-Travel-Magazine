import os
import json
import requests
import xml.etree.ElementTree as ET
from clean_html import clean_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def load_config(path=None):
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_item(item_el, config):
    title = (item_el.findtext("title") or "").strip()
    url = (item_el.findtext("link") or "").strip()
    guid = (item_el.findtext("guid") or url).strip()
    pub_date = (item_el.findtext("pubDate") or "").strip()

    raw_html = item_el.findtext("content:encoded", namespaces=NS) or ""
    cleaned_html = clean_html(raw_html)

    # Substack's RSS feed includes the cover image as an <enclosure> tag
    thumbnail_url = None
    enclosure = item_el.find("enclosure")
    if enclosure is not None:
        thumbnail_url = enclosure.get("url")
    if not thumbnail_url:
        thumbnail_url = config["logo_square"]

    # The RSS feed doesn't include per-post tags, so we always use the defaults
    categories = config["default_categories"]

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

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    item_elements = channel.findall("item") if channel is not None else []

    items_xml = [build_item(item_el, config) for item_el in item_elements]

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
