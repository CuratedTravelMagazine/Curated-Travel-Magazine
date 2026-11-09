import html
import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

from clean_html import clean_html, _clean_substack_image_url


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SUBSTACK_FEED_URL = "https://curatedtravelmagazine.substack.com/feed"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/xml, text/xml, "
        "text/html;q=0.9, */*;q=0.8"
    ),
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def load_config(path=None):
    """Load the MSN feed configuration file."""
    if path is None:
        path = os.path.join(SCRIPT_DIR, "config.json")

    with open(path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def force_https(url):
    """Convert an HTTP URL to HTTPS when possible."""
    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("http://"):
        return "https://" + url[7:]

    return url


def xml_text(value):
    """Escape plain text so it can be safely inserted into XML."""
    if value is None:
        return ""

    return escape(
        str(value),
        {
            '"': "&quot;",
            "'": "&apos;",
        },
    )


def cdata(value):
    """
    Wrap text in CDATA.

    Split embedded CDATA closing sequences so they do not break the XML.
    """
    if value is None:
        value = ""

    safe_value = str(value).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe_value}]]>"


def rfc822(dt_str):
    """
    Convert a standard RSS date or rss2json-style date to RFC822.

    Examples accepted:
    Mon, 09 Nov 2026 13:30:00 GMT
    2026-11-09 13:30:00
    """
    if not dt_str:
        return ""

    dt_str = str(dt_str).strip()

    try:
        parsed_date = parsedate_to_datetime(dt_str)

        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        else:
            parsed_date = parsed_date.astimezone(timezone.utc)

        return parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

    except (TypeError, ValueError, OverflowError):
        pass

    try:
        parsed_date = datetime.strptime(
            dt_str,
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)

        return parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

    except (TypeError, ValueError):
        return ""


def get_tag_text(item, tag_name, default=""):
    """Safely retrieve text from an RSS element."""
    tag = item.find(tag_name)

    if tag is None:
        return default

    return tag.get_text(strip=True)


def find_first_content_image(raw_html):
    """Find the first usable image URL inside an article body."""
    if not raw_html:
        return ""

    article_soup = BeautifulSoup(raw_html, "html.parser")

    for image in article_soup.find_all("img"):
        image_url = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-original")
            or ""
        )

        image_url = _clean_substack_image_url(image_url)

        if image_url and image_url.startswith("https://"):
            return image_url

    return ""


def fetch_rss():
    """
    Fetch the native Substack RSS feed directly.

    The browser-style headers reduce the chance of the request being
    rejected when this script runs through GitHub Actions.
    """
    response = requests.get(
        SUBSTACK_FEED_URL,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    print(f"Substack response content type: {content_type}")

    feed_soup = BeautifulSoup(response.content, "xml")
    items = feed_soup.find_all("item")

    if not items:
        response_preview = response.text[:500].replace("\n", " ")

        raise RuntimeError(
            "The Substack feed returned no RSS items. "
            f"Response preview: {response_preview}"
        )

    posts = []

    for item in items:
        title = get_tag_text(item, "title")
        canonical_url = get_tag_text(item, "link")
        guid = get_tag_text(item, "guid", canonical_url)
        pub_date = get_tag_text(item, "pubDate")

        content_tag = item.find("content:encoded")
        description_tag = item.find("description")

        if content_tag is not None:
            raw_html = content_tag.get_text()
        elif description_tag is not None:
            raw_html = description_tag.get_text()
        else:
            raw_html = ""

        raw_html = html.unescape(raw_html).strip()

        if not raw_html:
            print(f"Skipping post with no article content: {title}")
            continue

        categories = [
            category.get_text(strip=True)
            for category in item.find_all("category")
            if category.get_text(strip=True)
        ]

        thumbnail = ""

        thumbnail_tag = item.find("media:thumbnail")

        if thumbnail_tag is not None:
            thumbnail = (
                thumbnail_tag.get("url")
                or thumbnail_tag.get_text(strip=True)
                or ""
            )

        content_tag_for_media = item.find("media:content")

        if not thumbnail and content_tag_for_media is not None:
            thumbnail = content_tag_for_media.get("url", "")

        enclosure_link = ""
        enclosure_tag = item.find("enclosure")

        if enclosure_tag is not None:
            enclosure_link = enclosure_tag.get("url", "")

        if not thumbnail:
            thumbnail = find_first_content_image(raw_html)

        posts.append(
            {
                "title": title,
                "canonical_url": canonical_url,
                "id": guid or canonical_url,
                "pub_date_raw": pub_date,
                "body_html": raw_html,
                "tags": categories,
                "thumbnail": thumbnail,
                "enclosure_link": enclosure_link,
            }
        )

    if not posts:
        raise RuntimeError(
            "The Substack feed contained items, but none had usable content."
        )

    print(f"Fetched {len(posts)} posts directly from Substack")
    return posts


def choose_image(entry, cleaned_html, config):
    """
    Choose the best available image.

    Order:
    1. RSS thumbnail
    2. RSS enclosure
    3. First image in the article
    4. Square Curated Travel Magazine logo
    """
    candidates = [
        entry.get("thumbnail"),
        entry.get("enclosure_link"),
        find_first_content_image(cleaned_html),
        config.get("logo_square"),
    ]

    for candidate in candidates:
        if not candidate:
            continue

        image_url = _clean_substack_image_url(candidate)
        image_url = force_https(image_url)

        if image_url.startswith("https://"):
            return image_url

    raise RuntimeError(
        f"No valid image could be found for: {entry.get('title', 'Untitled')}"
    )


def build_item(entry, config):
    """Convert one Substack RSS entry into one MSN RSS item."""
    raw_html = html.unescape(entry.get("body_html", ""))
    cleaned_html = clean_html(raw_html)

    image_url = choose_image(entry, cleaned_html, config)
    pub_date = rfc822(entry.get("pub_date_raw"))

    title = html.unescape(entry.get("title", "")).strip()
    canonical_url = force_https(entry.get("canonical_url", ""))
    entry_id = entry.get("id") or canonical_url

    logo_square = force_https(config["logo_square"])
    logo_horizontal = force_https(config["logo_horizontal"])
    site_link = force_https(config["site_link"])

    item_xml = [
        "<item>",
        f"  <title>{cdata(title)}</title>",
        f"  <domain>{xml_text(site_link)}</domain>",
        f"  <siteName>{cdata(config['site_title'])}</siteName>",
        f"  <logo-square>{xml_text(logo_square)}</logo-square>",
        f"  <logo-horizontal>{xml_text(logo_horizontal)}</logo-horizontal>",
        f"  <link>{xml_text(canonical_url)}</link>",
        (
            '  <guid isPermaLink="false">'
            f"{xml_text(entry_id)}"
            "</guid>"
        ),
        f"  <dc:creator>{cdata(config['author_name'])}</dc:creator>",
    ]

    if pub_date:
        item_xml.append(f"  <pubDate>{xml_text(pub_date)}</pubDate>")

    for category in entry.get("tags", []):
        category = html.unescape(str(category)).strip()

        if category:
            item_xml.append(
                f"  <category>{cdata(category)}</category>"
            )

    item_xml.append(
        f"  <media:thumbnail>{xml_text(image_url)}</media:thumbnail>"
    )

    hero_html = (
        f'<figure><img src="{html.escape(image_url, quote=True)}" '
        f'alt="{html.escape(title, quote=True)}"/></figure>'
    )

    article_html = hero_html + cleaned_html

    item_xml.extend(
        [
            f"  <content:encoded>{cdata(article_html)}</content:encoded>",
            "</item>",
        ]
    )

    return "\n".join(item_xml)


def build_feed(posts, config):
    """Build the complete MSN-compatible RSS document."""
    parsed_items = [build_item(entry, config) for entry in posts]

    last_build = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    channel_logo = force_https(config["logo_square"])
    site_link = force_https(config["site_link"])
    feed_url = force_https(config["feed_url"])

    feed_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        ' xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        ' xmlns:media="http://search.yahoo.com/mrss/"',
        ' xmlns:wfw="http://wellformedweb.org/CommentAPI/"',
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"',
        ' xmlns:atom="http://www.w3.org/2005/Atom"',
        ' xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"',
        ' xmlns:slash="http://purl.org/rss/1.0/modules/slash/"',
        ' xmlns:georss="http://www.georss.org/georss"',
        ' xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">',
        "<channel>",
        f"  <title>{cdata(config['site_title'])}</title>",
        (
            f'  <atom:link href="{xml_text(feed_url)}" '
            'rel="self" type="application/rss+xml" />'
        ),
        f"  <link>{xml_text(site_link)}</link>",
        f"  <description>{cdata(config['site_description'])}</description>",
        f"  <lastBuildDate>{last_build}</lastBuildDate>",
        f"  <language>{xml_text(config['language'])}</language>",
        "  <sy:updatePeriod>hourly</sy:updatePeriod>",
        "  <sy:updateFrequency>1</sy:updateFrequency>",
        "  <image>",
        f"    <url>{xml_text(channel_logo)}</url>",
        f"    <title>{cdata(config['site_title'])}</title>",
        f"    <link>{xml_text(site_link)}</link>",
        "    <width>400</width>",
        "    <height>400</height>",
        "  </image>",
        "\n".join(parsed_items),
        "</channel>",
        "</rss>",
    ]

    return "\n".join(feed_xml)


def main():
    config = load_config()
    posts = fetch_rss()
    feed_xml = build_feed(posts, config)

    output_path = os.path.join(
        SCRIPT_DIR,
        config["output_file"],
    )

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(feed_xml)

    print(f"Generated MSN feed: {output_path}")
    print(f"Included {len(posts)} Substack posts")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
