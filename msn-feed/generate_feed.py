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

def rfc822(dt):
    try:
        return datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %z").strftime("%a, %d %b %Y %H:%M:%S %z")
    except:
        try:
            return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%a, %d %b %Y %H:%M:%S GMT")
        except:
            return ""

def fetch_rss():
    print("DEBUG: Fetching RSS feed…")
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
            "tags": [tag.term for tag in entry.tags] if hasattr(entry, "tags") else []
        }
        posts.append(item)

    return posts

def build_item(entry, config):
    title = entry["title"]
    url = entry["canonical_url"]
    guid = entry["id"]
    pub_date = rfc822(entry["post_date"])
    cleaned_html = clean_html(entry["body_html"])

    item_xml = []
    item_xml.append("<item>")
    item_xml.append(f"  <title>{title}</title>")
    item_xml.append(f"  <domain>{config['site_link']}</domain>")
    item_xml.append(f"  <siteName>{config['site_title']}</siteName>")
    item_xml.append(f"  <logo-square>{config['logo_square']}</logo-square>")
    item_xml.append(f"  <logo-horizontal>{config['logo_horizontal']}</logo-horizontal>")
    item_xml.append(f"  <link>{url}</link>")
    item_xml.append(f"  <guid isPermaLink=\"false\">{guid}</guid>")
    item_xml.append(f"  <dc:creator><![CDATA[{config['author_name']}]]></dc:creator>")
    item_xml.append(f"  <pubDate>{pub_date}</pubDate>")

    for cat in entry["tags"]:
        item_xml.append(f"  <category><![CDATA[{cat}]]></category>")

    item_xml.append("  <content:encoded><![CDATA[")
    item_xml.append(cleaned_html)
    item_xml.append("  ]]></content:encoded>")
    item_xml.append("</item>")

    return "\n".join(item_xml)

def main():
    config = load_config()
    print("DEBUG: Loaded config:", config)

    posts = fetch_rss()
    if not posts:
        print("DEBUG: No posts found — exiting.")
        return

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
    print("DEBUG: Writing feed to:", output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feed_xml))

    print("DEBUG: Feed generation complete.")

if __name__ == "__main__":
    main()
