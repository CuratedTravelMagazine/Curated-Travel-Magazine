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


def _clean_substack_image_url(src: str) -> str:
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


def _is_photo_credit_paragraph(p_tag):
    text = p_tag.get_text(strip=True)
    return bool(PHOTO_CREDIT_RE.match(text))


def _move_photo_credits_into_figcaptions(soup):
    """
    Find <p> tags that look like photo-credit lines and move their text
    into the <figcaption> of the nearest preceding <figure> that
    doesn't already have one.
    """
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

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    for tag in soup.find_all(["button", "svg", "source"]):
        tag.decompose()

    for tag in soup.find_all("picture"):
        tag.unwrap()

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
            if isinstance(child, NavigableString):
                continue
            if child.name not in ["img", "figcaption"]:
                child.unwrap()

    # Remove any <figure> with no image and no text BEFORE attaching credits,
    # so a photo credit doesn't get attached to a stray empty duplicate figure
    _remove_empty_figures(soup)

    # Move "Photo Credit: ..." paragraphs into the nearest remaining figure's figcaption
    _move_photo_credits_into_figcaptions(soup)

    return str(soup)
