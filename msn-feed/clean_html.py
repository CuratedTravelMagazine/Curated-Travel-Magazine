from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs, urlunparse

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i", "u",
    "h1", "h2", "h3", "h4",
    "figure", "figcaption",
    "img", "a"
}

def _clean_substack_image_url(src: str) -> str:
    """
    Rewrite Substack CDN URLs to direct S3 URLs and convert webp → jpg.
    """
    if "substackcdn.com/image/fetch" in src:
        parts = src.split("/")
        for segment in reversed(parts):
            if "substack-post-media.s3.amazonaws.com" in segment or "%2Fsubstack-post-media.s3.amazonaws.com" in segment:
                decoded = segment.replace("%3A", ":").replace("%2F", "/")
                src = decoded
                break

    src = src.replace("%3A", ":").replace("%2F", "/")
    src = re.sub(r"\.webp(\b|$)", ".jpg", src)

    return src

def _strip_unwanted_attributes(tag):
    allowed_attrs = {"href", "src", "alt", "title"}
    for attr in list(tag.attrs.keys()):
        if attr.startswith("data-"):
            del tag.attrs[attr]
        elif attr not in allowed_attrs:
            del tag.attrs[attr]

def _clean_links(tag):
    href = tag.get("href")
    if not href:
        return

    parsed = urlparse(href)
    qs = parse_qs(parsed.query)

    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "action"]:
        qs.pop(key, None)

    new_query = "&".join(f"{k}={v[0]}" for k, v in qs.items() if v)
    cleaned = urlunparse(parsed._replace(query=new_query))
    tag["href"] = cleaned

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml-xml")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    for tag in soup.find_all(["button", "svg", "picture", "source"]):
        tag.decompose()

    for tag in soup.find_all("p", class_="button-wrapper"):
        tag.decompose()

    for tag in soup.find_all("hr"):
        tag.decompose()

    for fig in soup.find_all("figure"):
        for a in fig.find_all("a"):
            a.unwrap()

    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        if "class" in tag.attrs:
            del tag.attrs["class"]

        _strip_unwanted_attributes(tag)

        if tag.name == "img":
            src = tag.get("src")
            if src:
                tag["src"] = _clean_substack_image_url(src)

        if tag.name == "a":
            _clean_links(tag)

    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if not h.get_text(strip=True):
            h.decompose()

    for fig in soup.find_all("figure"):
        for child in list(fig.contents):
            if child.name not in ["img", "figcaption"]:
                child.unwrap()

    return str(soup)
