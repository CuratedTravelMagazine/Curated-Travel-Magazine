from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse
import re

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i", "u",
    "h1", "h2", "h3", "h4",
    "figure", "figcaption",
    "img", "a"
}

def _clean_substack_image_url(src: str) -> str:
    """
    Rewrite Substack CDN URLs to direct S3 URLs and convert webp to jpg.
    Example input:
      https://substackcdn.com/image/fetch/.../https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fxxx.webp
    Output:
      https://substack-post-media.s3.amazonaws.com/public/images/xxx.jpg
    """
    if "substackcdn.com/image/fetch" in src:
        # Extract the final URL after the last '/'
        parts = src.split("/")
        # Find the last segment that looks like an encoded URL
        for segment in reversed(parts):
            if "substack-post-media.s3.amazonaws.com" in segment or "%2Fsubstack-post-media.s3.amazonaws.com" in segment:
                # Decode percent-encoding
                decoded = segment.replace("%3A", ":").replace("%2F", "/")
                src = decoded
                break

    # If still percent-encoded, decode basic path
    src = src.replace("%3A", ":").replace("%2F", "/")

    # Convert webp to jpg (MSN does not accept webp) 
    src = re.sub(r"\.webp(\b|$)", ".jpg", src)

    return src

def _strip_unwanted_attributes(tag):
    """
    Remove Substack-specific attributes and classes.
    Keep only href/src/alt/title on allowed tags.
    """
    allowed_attrs = {"href", "src", "alt", "title"}
    attrs_to_delete = []

    for attr in list(tag.attrs.keys()):
        if attr.startswith("data-") or attr in ["fetchpriority"]:
            attrs_to_delete.append(attr)
        elif attr not in allowed_attrs:
            attrs_to_delete.append(attr)

    for attr in attrs_to_delete:
        del tag.attrs[attr]

def _clean_links(tag):
    """
    Clean <a> hrefs: remove tracking params like utm_source, utm_medium, etc.
    """
    href = tag.get("href")
    if not href:
        return

    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    # Drop common tracking params
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "action"]:
        qs.pop(key, None)

    new_query = "&".join(
        f"{k}={v[0]}" for k, v in qs.items() if v
    )
    cleaned = urlunparse(parsed._replace(query=new_query))
    tag["href"] = cleaned

def clean_html(html: str) -> str:
    """
    Clean Substack HTML for MSN/SimpleFeed:
    - remove scripts, buttons, svg, picture, source
    - rewrite image URLs to direct S3 jpg/png
    - strip Substack UI and tracking
    - keep only allowed tags and attributes
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts and style
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Remove Substack UI elements
    for tag in soup.find_all(["button", "svg", "picture", "source"]):
        tag.decompose()

    # Walk all tags and clean
    for tag in soup.find_all(True):
        # Drop tags not in allowed list, but keep their contents
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        # Clean attributes
        _strip_unwanted_attributes(tag)

        # Special handling for images
        if tag.name == "img":
            src = tag.get("src")
            if src:
                cleaned_src = _clean_substack_image_url(src)
                tag["src"] = cleaned_src

        # Special handling for links
        if tag.name == "a":
            _clean_links(tag)

    # Optional: ensure figures have figcaptions if there is a nearby "Photo credit" text
    for fig in soup.find_all("figure"):
        has_caption = bool(fig.find("figcaption"))
        if not has_caption:
            # Look for a following <p> with "Photo credit:"
            next_p = fig.find_next_sibling("p")
            if next_p and "Photo credit:" in next_p.get_text():
                caption = soup.new_tag("figcaption")
                caption.string = next_p.get_text()
                fig.append(caption)
                next_p.decompose()

    # Return cleaned HTML as string
    cleaned = str(soup)
    return cleaned

