def _clean_substack_image_url(src: str) -> str:
    if not src:
        return ""

    src = src.strip()

    # Decode common URL encoding first
    src = src.replace("%3A", ":").replace("%2F", "/")

    # Substack CDN pattern: .../image/fetch/.../https://substack-post-media.s3.amazonaws.com/...
    # Extract the real S3 URL that appears after the last "https://"
    if "substackcdn.com/image/fetch" in src or "substack-post-media.s3.amazonaws.com" in src:
        # Find the last occurrence of the real image host
        marker = "https://substack-post-media.s3.amazonaws.com"
        idx = src.rfind(marker)
        if idx != -1:
            src = src[idx:]
            # Clean any trailing junk after the image extension
            src = re.split(r"[?\s\"']", src)[0]

    # Prefer .jpg over .webp
    src = re.sub(r"\.webp(\b|$)", ".jpg", src)

    # Force HTTPS
    if src.startswith("http://"):
        src = "https://" + src[7:]

    # Reject bare domains or incomplete URLs
    if not re.match(r"^https://[^/]+/.+\.(jpe?g|png|gif|webp)$", src, re.IGNORECASE):
        return ""

    return src
