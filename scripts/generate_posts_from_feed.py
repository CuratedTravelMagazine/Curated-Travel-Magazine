import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
import re

FEED_URL = "https://www.curatedtravelmagazine.com/msn-feed/msn-feed.xml"

POSTS_DIR = "_posts"
IMAGES_DIR = "blog/assets/images/blog"   # ← YOUR CORRECT DIRECTORY

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

def rfc822_to_date(pubdate):
    dt = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S GMT")
    return dt.strftime("%Y-%m-%d")

def sanitize_title_for_filename(title):
    cleaned = re.sub(r'[^A-Za-z0-9]', '', title)
    return cleaned.upper()

resp = requests.get(FEED_URL)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "xml")
items = soup.find_all("item")

for item in items:
    title = item.find("title").text.strip()
    pubdate = item.find("pubDate").text.strip()
    date = rfc822_to_date(pubdate)

    thumbnail_url = item.find("media:thumbnail").text.strip()
    content = item.find("content:encoded").text

    safe_title = sanitize_title_for_filename(title)

    # Local image filename
    image_filename = f"{safe_title}.jpg"
    image_path = os.path.join(IMAGES_DIR, image_filename)

    # Download image
    try:
        img_data = requests.get(thumbnail_url).content
        with open(image_path, "wb") as img_file:
            img_file.write(img_data)
        print(f"Downloaded image: {image_path}")
    except Exception as e:
        print(f"Failed to download image for {title}: {e}")

    # Build post filename
    post_filename = f"{date}-{safe_title}.md"
    post_path = os.path.join(POSTS_DIR, post_filename)

    # Write blog post
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(f"layout\tpost\n")
        f.write(f"title\t{title}\n")
        f.write(f"date\t{date}\n")
        f.write(f"image\t/blog/assets/images/blog/{image_filename}\n")
        f.write(f"featured_image\t/blog/assets/images/blog/{image_filename}\n\n")
        f.write(content)

    print(f"Created blog post: {post_path}")

