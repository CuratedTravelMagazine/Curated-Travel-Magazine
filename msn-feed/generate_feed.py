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
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return ""


def fetch_rss():
    rss2json_url = (
        "https://api.rss2json.com/v1/api.json"
        "?rss_url=https%3A%2F%2Fcuratedtravelmagazine.substack.com%2Ffeed"
    )
    resp = requests.get(rss2json_url)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"rss2json returned an error: {data}")

    posts = []
    for item in data.get("items", []):
        raw_html = item.get("content") or item.get("description") or ""
        if not raw_html:
            continue

        thumbnail = item.get("thumbnail")
        enclosure = item.get("enclosure", {}) or {}
        enclosure_link = enclosure.get("link")

        posts.append({
            "title": item.get("title", ""),
            "canonical_url": item.get("link", ""),
            "id": item.get("guid") or item.get("link", ""),
            "pub_date_raw": item.get("pubDate"),
            "body_html": raw_html,
            "tags": item.get("categories") or [],
            "thumbnail": thumbnail,
            "enclosure_link": enclosure_link,
        })

    return posts



def extract_thumbnail(cleaned_html, fallback):
    soup = BeautifulSoup(cleaned_html, "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return fallback


def build_item(entry, config):
    raw_html = entry["body_html"]

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

    item_xml.append(f"  <media:thumbnail>{thumbnail_url}</media:thumbnail>")
    item_xml.append("  <content:encoded><![CDATA[")
    item_xml.append(cleaned_html)
    item_xml.append("  ]]></content:encoded>")
    item_xml.append("</item>")

    return "\n".join(item_xml)


def main():
    config = load_config()
    posts = fetch_posts()

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
