import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag


class LinkExtractor(HTMLParser):

    def __init__(self, base_url=""):
        super().__init__()
        self.base_url = base_url
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href" and value:
                    full_url = urljoin(self.base_url, value)
                    full_url, _ = urldefrag(full_url)
                    self.links.add(full_url)


def extract_links(html, base_url=""):
    extractor = LinkExtractor(base_url)
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.links


def extract_meta(html, name):
    pattern = re.compile(
        r'<meta\s+[^>]*name=["\']' + re.escape(name) + r'["\'][^>]*content=["\']([^"\']+)["\']',
        re.IGNORECASE
    )
    match = pattern.search(html)
    return match.group(1) if match else None
