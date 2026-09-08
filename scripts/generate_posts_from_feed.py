import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
import re

# Your feed URL
FEED_URL = "https://www.curatedtravelmagazine.com/msn-feed/msn-feed.xml"

# Output directory for Jekyll/Hugo-style posts
OUTPUT_DIR = "_posts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def rfc822_to_date(pubdate):
    """Convert RSS pubDate (RFC822) → YYYY-MM-DD."""
    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S GMT")
    return dt.strftime("%Y-%m-%d")

def sanitize_title_for_filename(title):
    """Remove all non-alphanumeric characters and uppercase the title."""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', title)
    return cleaned.upper()

# Fetch the XML feed
resp = requests.get(FEED_URL)
resp.raise_for_status()

# Use the standard XML parser (works once lxml is installed in Actions)
soup = BeautifulSoup(resp.text, "xml")

items = soup.find_all("item")

for item in items:
    title = item.find("title").text.strip()
    pubdate = item.find("pubDate").text.strip()
    date = rfc822_to_date(pubdate)

    thumbnail = item.find("media:thumbnail").text.strip()
    content = item.find("content:encoded").text

    # Build filename: YYYY-MM-DD-TITLEWITHOUTSPACES.md
    safe_title = sanitize_title_for_filename(title)
    filename = f"{date}-{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Write blog post file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"layout\tpost\n")
        f.write(f"title\t{title}\n")
        f.write(f"date\t{date}\n")
        f.write(f"image\t{thumbnail}\n")
        f.write(f"featured_image\t{thumbnail}\n\n")
        f.write(content)

    print(f"Created blog post: {filepath}")
