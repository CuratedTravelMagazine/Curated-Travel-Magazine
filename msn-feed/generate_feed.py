import os
import json
import time
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
from clean_html import clean_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def rfc822_from_struct(time_struct):
    """Convert feedparser's parsed time struct into RFC822 format for RSS."""
    if not time_struct:
        return ""
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time_struct)


def fetch_rss():
    rss_url = "https://curatedtravelmagazine.substack.com/feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    resp = requests.get(rss_url, headers=headers)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)

    posts = []

    for entry in feed.entries:
        raw_html = None

        if hasattr(entry, "content") and entry.content:
            raw_html = entry.content[0].value
        elif hasattr(entry, "summary") and entry.summary:
            raw_html = entry.summary
        elif hasattr(entry, "description") and entry.description:
            raw_html = entry.description

        if not raw_html:
            continue

        posts.append({
            "title": entry.title,
            "canonical_url": entry.link,
            "id": entry.id,
            "published_parsed": getattr(entry, "published_parsed", None),
            "body_html": raw_html,
            "tags": [tag.term for tag in entry.tags] if hasattr(entry, "tags") else []
        })

    return posts


def extract_thumbnail(cleaned_html, config):
    soup = BeautifulSoup(cleaned_html, "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return config["logo_square"]


def build_item(entry, config):
    raw_html = entry["body_html"]

    # Decode HTML entities before cleaning
    raw_html = (
        raw_html.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
    )

    cleaned_html = clean_html(raw_html)
    thumbnail_url = extract_thumbnail(cleaned_html, config)
    pub_date = rfc822_from_struct(entry["published_parsed"])

    title = (
        entry["title"]
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )

    item_xml = []
    item_xml.append("<item>")
    item_xml.append(f"  <title><![CDATA[{title}]]></title>")
    item_xml.append(f"  <domain>{config['site_link']}</domain>")
    item_xml.append(f"  <siteName>{config['site_title']}</siteName>")
    item_xml.append(f"  <logo-square>{config['logo_square']}</logo-square>")
    item_xml.append(f"  <logo-horizontal>{config['logo_horizontal']}</logo-horizontal>")
    item_xml.append(f"  <link>{entry['canonical_url']}</link>")
    item_xml.append(f"  <guid isPermaLink=\"false\">{entry['id']}</guid>")
    item_xml.append(f"  <dc:creator><![CDATA[{config['author_name']}]]></dc:creator>")
    if pub_date:
        item_xml.append(f"  <pubDate>{pub_date}</pubDate>")

    for cat in entry["tags"]:
        item_xml.append(f"  <category><![CDATA[{cat}]]></category>")

    item_xml.append(f"  <media:thumbnail>{thumbnail_url}</media:thumbnail>")
    item_xml.append("  <content:encoded><![CDATA[")
    item_xml.append(cleaned_html)
    item_xml.append("  ]]></content:encoded>")
    item_xml.append("</item>")

    return "\n".join(item_xml)


def main():
    config = load_config()
    posts = fetch_rss()

    parsed_items = [build_item(entry, config) for entry in posts]

    last_build = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    feed_xml = []
    feed_xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    feed_xml.append('<rss version="2.0"')
    feed_xml.append(' xmlns:content="http://purl.org/rss/1.0/modules/content/"')
    feed_xml.append(' xmlns:media="http://search.yahoo.com/mrss/"')
    feed_xml.append(' xmlns:wfw="http://wellformedweb.org/CommentAPI/"')
    feed_xml.append(' xmlns:dc="http://purl.org/dc/elements/1.1/"')
    feed_xml.append(' xmlns:atom="http://www.w3.org/2005/Atom"')
    feed_xml.append(' xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"')
    feed_xml.append(' xmlns:slash="http://purl.org/rss/1.0/modules/slash/"')
    feed_xml.append(' xmlns:georss="http://www.georss.org/georss"')
    feed_xml.append(' xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#"')
    feed_xml.append('>')
    feed_xml.append('<channel>')
    feed_xml.append(f"  <title>{config['site_title']}</title>")
    feed_xml.append(f"  <atom:link href=\"{config['feed_url']}\" rel=\"self\" type=\"application/rss+xml\" />")
    feed_xml.append(f"  <link>{config['site_link']}</link>")
    feed_xml.append(f"  <description>{config['site_description']}</description>")
    feed_xml.append(f"  <lastBuildDate>{last_build}</lastBuildDate>")
    feed_xml.append("  <sy:updatePeriod>hourly</sy:updatePeriod>")
    feed_xml.append("  <sy:updateFrequency>1</sy:updateFrequency>")
    feed_xml.append("  <image>")
    feed_xml.append(f"    <url>{config['logo_square']}</url>")
    feed_xml.append(f"    <title>{config['site_title']}</title>")
    feed_xml.append(f"    <link>{config['site_link']}</link>")
    feed_xml.append("    <width>400</width>")
    feed_xml.append("    <height>400</height>")
    feed_xml.append("  </image>")
    feed_xml.append("\n".join(parsed_items))
    feed_xml.append("</channel>")
    feed_xml.append("</rss>")

    output_path = os.path.join(SCRIPT_DIR, config["output_file"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feed_xml))


if __name__ == "__main__":
    main()
