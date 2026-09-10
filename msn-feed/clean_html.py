from bs4 import BeautifulSoup, NavigableString
import re
from urllib.parse import urlparse, parse_qs, urlunparse

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i", "u",
    "h1", "h2", "h3", "h4",
    "figure", "figcaption",
    "img", "a"
}

PHOTO_CREDIT_RE = re.compile(r"^\s*photo\s*credit\s*:?\s*", re.IGNORECASE)

# Patterns that indicate Substack footer / subscription text
FOOTER_PATTERNS = [
    re.compile(r"thanks for reading", re.IGNORECASE),
    re.compile(r"this post is public so feel free to share it", re.IGNORECASE),
    re.compile(r"about curated travel magazine", re.IGNORECASE),
    re.compile(r"is a reader-supported publication", re.IGNORECASE),
    re.compile(r"to receive new posts and support my work", re.IGNORECASE),
    re.compile(r"consider becoming a free or paid subscriber", re.IGNORECASE),
    re.compile(r"purchase the current edition", re.IGNORECASE),
    re.compile(r"the latest issue is also available in print", re.IGNORECASE),
]


def _clean_substack_image_url(src: str) -> str:
    if not src:
        return ""

    src = src.strip()

    # Decode common URL encoding
    src = src.replace("%3A", ":").replace("%2F", "/")

    # Unwrap Substack CDN fetch URLs
    if "substackcdn.com/image/fetch" in src:
        parts = src.split("/")
        for segment in reversed(parts):
            if "substack-post-media.s3.amazonaws.com" in segment or "%2Fsubstack-post-media.s3.amazonaws.com" in segment:
                decoded = segment.replace("%3A", ":").replace("%2F", "/")
                src = decoded
                break

    # Prefer .jpg over .webp
    src = re.sub(r"\.webp(\b|$)", ".jpg", src)

    # Force HTTPS
    if src.startswith("http://"):
        src = "https://" + src[7:]

    # If the src is just a bare domain (no path), treat it as invalid
    if re.match(r"^https?://[^/]+/?$", src):
        return ""

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


def _is_photo_credit_paragraph(p_tag):
    text = p_tag.get_text(strip=True)
    return bool(PHOTO_CREDIT_RE.match(text))


def _is_footer_paragraph(p_tag):
    text = p_tag.get_text(strip=True)
    if not text:
        return False
    for pattern in FOOTER_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _move_photo_credits_into_figcaptions(soup):
    credit_paragraphs = [p for p in soup.find_all("p") if _is_photo_credit_paragraph(p)]

    for p_tag in credit_paragraphs:
        credit_text = p_tag.get_text(strip=True)
        credit_text = PHOTO_CREDIT_RE.sub("", credit_text).strip()

        preceding_figures = p_tag.find_all_previous("figure")
        target_figure = None
        for fig in preceding_figures:
            if not fig.find("figcaption"):
                target_figure = fig
                break

        if target_figure is not None and credit_text:
            figcaption = soup.new_tag("figcaption")
            figcaption.string = f"Photo Credit: {credit_text}"
            target_figure.append(figcaption)

        p_tag.decompose()


def _remove_empty_figures(soup):
    for fig in soup.find_all("figure"):
        has_img = fig.find("img") is not None
        has_text = bool(fig.get_text(strip=True))
        if not has_img and not has_text:
            fig.decompose()


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, buttons, etc.
    for tag in soup.find_all(["script", "style", "button", "svg", "source"]):
        tag.decompose()

    for tag in soup.find_all("picture"):
        tag.unwrap()

    for tag in soup.find_all("p", class_="button-wrapper"):
        tag.decompose()

    for tag in soup.find_all("hr"):
        tag.decompose()

    # Unwrap links inside figures
    for fig in soup.find_all("figure"):
        for a in fig.find_all("a"):
            a.unwrap()

    # Keep only allowed tags and clean attributes
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        if "class" in tag.attrs:
            del tag.attrs["class"]

        _strip_unwanted_attributes(tag)

        if tag.name == "img":
            src = tag.get("src")
            cleaned = _clean_substack_image_url(src) if src else ""
            if cleaned:
                tag["src"] = cleaned
            else:
                tag.decompose()
                continue

        if tag.name == "a":
            _clean_links(tag)

    # Remove empty headings
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if not h.get_text(strip=True):
            h.decompose()

    # Clean figure children
    for fig in soup.find_all("figure"):
        for child in list(fig.contents):
            if isinstance(child, NavigableString):
                continue
            if child.name not in ["img", "figcaption"]:
                child.unwrap()

    # Remove any remaining images with incomplete src
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not re.match(r"^https://[^/]+/.+", src):
            img.decompose()

    _remove_empty_figures(soup)
    _move_photo_credits_into_figcaptions(soup)

    # Remove Substack footer paragraphs
    for p in soup.find_all("p"):
        if _is_footer_paragraph(p):
            p.decompose()

    # Remove any remaining empty paragraphs
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()

    return str(soup)
