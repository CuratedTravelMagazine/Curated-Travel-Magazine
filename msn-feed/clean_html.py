import re
from html import unescape

def clean_html(raw_html: str) -> str:
    """
    Take Substack HTML from the API and return MSN-safe HTML:
    - remove scripts and subscription widgets
    - keep basic tags (p, h1-h4, figure, img, a, strong, em, blockquote)
    - strip most Substack-specific wrappers
    """

    html = raw_html

    # Unescape any HTML entities
    html = unescape(html)

    # Remove <script> blocks completely
    html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove subscription widgets, share buttons, restack, etc. by class hints
    html = re.sub(r'<div[^>]*subscription-widget[^>]*>.*?</div>', "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<div[^>]*captioned-button-wrap[^>]*>.*?</div>', "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<div[^>]*restack-image[^>]*>.*?</div>', "", html, flags=re.DOTALL | re.IGNORECASE)

    # Strip generic div wrappers but keep inner content
    html = re.sub(r"<div[^>]*>", "", html)
    html = html.replace("</div>", "")

    # Strip span wrappers but keep inner content
    html = re.sub(r"<span[^>]*>", "", html)
    html = html.replace("</span>", "")

    # Optional: normalize h-tags (keep them)
    # No change needed unless you want to force h3/h4 only

    # Remove empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    # Basic cleanup of excessive whitespace
    html = re.sub(r"\s+\n", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)

    return html.strip()
