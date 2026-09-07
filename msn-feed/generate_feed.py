import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from clean_html import clean_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def rfc822(dt_str):
    """
    Convert Substack pubDate → RFC822
    Example input: "Mon, 02 Sep 2026 08:58:40 +0000"
    """
    try:
        dt = datetime.strptime(dt_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return ""


def fetch_rss():
    """
    Fetch the REAL Substack RSS feed.
    This preserves <img> tags inside <content:encoded>.
    """
    rss_url = "https://curatedtravelmagazine.substack.com/feed"

    resp = requests.get(
        rss_url,
        headers={"User-Agent": "Mozilla/5.0"}  # prevents Substack bot blocking
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "xml")
    items = soup.find_all("item")

    posts = []
    for item in items:
        title = item.find("title").text if item.find("title") else ""
        link = item.find("link").text if item.find("link") else ""
        guid = item.find("guid").text if item.find("guid") else link
        pub_date = item.find("pubDate").text if item.find("pubDate") else ""

        encoded = item.find("content:encoded")
        raw_html = encoded.text if encoded else ""

        tags = [c.text for c in item.find_all("category")]

        posts.append({
            "title": title,
            "canonical_url": link,
            "id": guid,
            "pub_date_raw": pub_date,
            "body_html": raw_html,
            "tags": tags
        })

    return posts


def extract_thumbnail(cleaned_html, fallback):
    """
    Extract the first <img> from cleaned HTML.
    If none found, use fallback logo.
    """
    soup = BeautifulSoup(cleaned_html, "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return fallback


def build_item(entry, config):
    raw_html = entry["body_html"]

    # Decode HTML entities before cleaning
    raw_html = (
        raw_html.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
    )

    cleaned_html = clean_html(raw_html)
    thumbnail_url = extract_thumbnail(cleaned_html, config["logo_square"])
    pub_date = rfc822(entry["pub_date_raw"])

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

    # MSN thumbnail
    item_xml.append(f"  <media:thumbnail>{thumbnail_url}</media:thumbnail>")

    # Full HTML content
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

    # Insert all items
    feed_xml.append("\n".join(parsed_items))

    feed_xml.append("</channel>")
    feed_xml.append("</rss>")

    output_path = os.path.join(SCRIPT_DIR, config["output_file"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feed_xml))


if __name__ == "__main__":
    main()
