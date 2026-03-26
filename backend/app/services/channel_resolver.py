import re
import httpx


def resolve_channel_id(url_or_id: str) -> tuple[str, str]:
    url_or_id = url_or_id.strip()
    if not url_or_id:
        raise ValueError("Empty channel URL or ID")

    # Raw channel ID
    if re.match(r"^UC[\w-]{22}$", url_or_id):
        return url_or_id, url_or_id

    # /channel/UCxxxx URL
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url_or_id)
    if m:
        return m.group(1), m.group(1)

    # /@handle or /c/name URL — fetch page to extract channel ID
    if re.search(r"youtube\.com/(@[\w.-]+|c/[\w.-]+)", url_or_id):
        return _fetch_channel_id_from_page(url_or_id)

    raise ValueError(f"Cannot resolve channel from: {url_or_id}")


def _fetch_channel_id_from_page(url: str) -> tuple[str, str]:
    resp = httpx.get(url, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    m = re.search(r'<meta\s+itemprop="identifier"\s+content="(UC[\w-]+)"', resp.text)
    if not m:
        m = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
    if not m:
        raise ValueError(f"Could not find channel ID in page: {url}")
    channel_id = m.group(1)
    name_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', resp.text)
    name = name_match.group(1) if name_match else channel_id
    return channel_id, name
