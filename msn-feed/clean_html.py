from bs4 import BeautifulSoup, NavigableString
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
    Normalize Substack image URLs:
    - Decode percent-encoding
    - Extract direct S3 URL from Substack CDN wrapper
    - Convert .webp → .jpg for MSN compatibility
    """
    if not src:
        return src

    # Decode common percent-encoding first
    src = src.replace("%3A", ":").replace("%2F", "/")

    # If it's a Substack CDN wrapper, extract the underlying S3 URL
    if "substackcdn.com/image/fetch" in src:
        parts = src.split("/")
        for segment in reversed(parts):
            if "substack-post-media.s3.amazonaws.com" in segment:
                src = segment
                break

    # Always convert webp → jpg at the end
    src = re.sub(r"\.webp(\b|$)", ".jpg", src)

    return src

def _strip_unwanted_attributes(tag):
    """
    Keep only safe, content-related attributes.
    Remove data-* and layout/JS-related attributes.
    """
    allowed_attrs = {"href", "src", "alt", "title"}
    for attr in list(tag.attrs.keys()):
        if attr.startswith("data-"):
            del tag.attrs[attr]
        elif attr not in allowed_attrs:
            del tag.attrs[attr]

def _clean_links(tag):
    """
    Strip tracking parameters from links (UTM, action, etc.).
    """
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
    """
    Clean Substack article HTML for MSN:
    - Remove scripts, styles, UI chrome
    - Normalize images and links
    - Preserve editorial structure (p, headings, figure, figcaption, img, a)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts and styles
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Remove Substack UI elements (buttons, SVG icons, responsive picture/source)
    for tag in soup.find_all(["button", "svg", "picture", "source"]):
        tag.decompose()

    # Remove share button wrappers
    for tag in soup.find_all("p", class_="button-wrapper"):
        tag.decompose()

    # Remove horizontal rules
    for tag in soup.find_all("hr"):
        tag.decompose()

    # Unwrap <a> inside <figure> so <img> is a direct child
    for fig in soup.find_all("figure"):
        for a in fig.find_all("a"):
            a.unwrap()

    # Clean tags and attributes
    for tag in soup.find_all(True):
        # For tags not in ALLOWED_TAGS, unwrap but keep text
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        # Strip classes
        if "class" in tag.attrs:
            del tag.attrs["class"]

        # Strip unwanted attributes
        _strip_unwanted_attributes(tag)

        # Normalize images
        if tag.name == "img":
            src = tag.get("src")
            if src:
                tag["src"] = _clean_substack_image_url(src)

        # Clean links
        if tag.name == "a":
            _clean_links(tag)

    # Remove empty headings
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if not h.get_text(strip=True):
            h.decompose()

    # Ensure <figure> contains only <img> and <figcaption> (plus text nodes)
    for fig in soup.find_all("figure"):
        for child in list(fig.contents):
            if isinstance(child, NavigableString):
                continue
            if child.name not in ["img", "figcaption"]:
                child.unwrap()

    return str(soup)
