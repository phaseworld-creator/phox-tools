import concurrent.futures
import re
import time
from urllib.parse import urljoin, urlparse, urldefrag
from pathlib import Path

from phox.config import success, error, info, warning, OUTPUT_DIR, CLONED_DIR
from phox.lib.http import get as http_get


BINARY_TYPES = (
    "image/", "font/", "video/", "audio/",
    "application/octet-stream", "application/pdf",
    "application/zip", "application/x-font",
)

TEXT_TYPES = (
    "text/html", "text/css", "text/javascript",
    "application/javascript", "text/plain", "application/json",
)


def parse_robots_txt(base_url):
    robots_url = urljoin(base_url, "/robots.txt")
    disallowed = set()
    try:
        resp = http_get(robots_url, timeout=5,
                        headers={"User-Agent": "PhoxCloner/1.0"})
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)
    except Exception:
        pass
    return disallowed


def is_allowed(url, base_domain, disallowed_paths):
    parsed = urlparse(url)
    if parsed.hostname != base_domain:
        return True
    for path in disallowed_paths:
        if parsed.path.startswith(path):
            return False
    return True


def url_to_filepath(url, output_dir):
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return output_dir / "index.html"

    ext = Path(path).suffix.lower()

    if ext in ("", ".html", ".htm", ".php", ".asp", ".aspx", ".jsp"):
        if ext:
            path = path[:-len(ext)]
        return output_dir / (path + ".html")

    return output_dir / path


def fetch_url(u):
    try:
        r = http_get(u, timeout=10, headers={"User-Agent": "PhoxCloner/1.0"})
        ct = r.headers.get("content-type", "")
        raw = r.content
        text = ""
        if any(ct.startswith(t) for t in TEXT_TYPES):
            text = raw.decode("utf-8", errors="replace")
        return u, r.status_code, ct, text, raw
    except Exception as e:
        return u, None, "", str(e), b""


def extract_page_links(html, base_url):
    links = set()
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.I):
        full = urljoin(base_url, urldefrag(m.group(1))[0])
        links.add(full)
    return links


def extract_html_assets(html, base_url):
    assets = set()
    patterns = [
        r'<link\s[^>]*href=["\']([^"\']+)["\']',
        r'<script\s[^>]*src=["\']([^"\']+)["\']',
        r'<img\s[^>]*src=["\']([^"\']+)["\']',
        r'<source\s[^>]*src=["\']([^"\']+)["\']',
        r'<video\s[^>]*poster=["\']([^"\']+)["\']',
        r'<(?:video|audio)\s[^>]*src=["\']([^"\']+)["\']',
        r'<object\s[^>]*data=["\']([^"\']+)["\']',
        r'<embed\s[^>]*src=["\']([^"\']+)["\']',
        r'<iframe\s[^>]*src=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+\.(?:png|jpe?g|gif|svg|webp))["\']',
        r'url\(["\']?([^"\')\s]+)["\']?\)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.I):
            val = m.group(1)
            full = urljoin(base_url, urldefrag(val)[0])
            assets.add(full)
    return assets

def extract_css_resources(css_text, css_url):
    """Extract @import and url() references from CSS."""
    assets = set()
    for m in re.finditer(r'@import\s+(?:url\(["\']?([^"\')\s]+)["\']?\)|["\']([^"\']+)["\'])', css_text, re.I):
        ref = m.group(1) or m.group(2)
        full = urljoin(css_url, urldefrag(ref)[0])
        assets.add(full)
    for m in re.finditer(r'url\(["\']?([^"\')\s]+)["\']?\)', css_text, re.I):
        ref = m.group(1)
        if ref.startswith("data:"):
            continue
        full = urljoin(css_url, urldefrag(ref)[0])
        assets.add(full)
    return assets


def extract_js_references(js_text, js_url):
    """Extract path-like string references from JavaScript (imports, fetch, etc)."""
    assets = set()
    for m in re.finditer(r'from\s+["\']([^"\']+)["\']', js_text):
        ref = m.group(1)
        if ref.startswith((".", "/", "http")):
            full = urljoin(js_url, urldefrag(ref)[0])
            assets.add(full)
    for m in re.finditer(r'import\s+["\']([^"\']+)["\']', js_text):
        ref = m.group(1)
        if ref.startswith((".", "/", "http")):
            full = urljoin(js_url, urldefrag(ref)[0])
            assets.add(full)
    for m in re.finditer(r'require\s*\(\s*["\']([^"\']+)["\']', js_text):
        ref = m.group(1)
        if ref.startswith((".", "/", "http")):
            full = urljoin(js_url, urldefrag(ref)[0])
            assets.add(full)
    for m in re.finditer(r'fetch\s*\(\s*["\']([^"\']+)["\']', js_text):
        full = urljoin(js_url, urldefrag(m.group(1))[0])
        assets.add(full)
    for m in re.finditer(r'["\'](?:src|href|url|path|file)["\']\s*:\s*["\']([^"\']+)["\']', js_text):
        ref = m.group(1)
        if ref.startswith(("http", "/", ".")):
            full = urljoin(js_url, urldefrag(ref)[0])
            assets.add(full)
    return assets


def clone_site(start_url, output_dir, max_depth=5, concurrency=10,
               respect_robots=True, delay=0.1):
    parsed = urlparse(start_url)
    base_domain = parsed.hostname
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    disallowed = set()
    if respect_robots:
        info("Checking robots.txt...")
        disallowed = parse_robots_txt(start_url)
        if disallowed:
            info(f"Found {len(disallowed)} disallowed paths")

    visited = set()
    to_visit = [(start_url, 0)]
    pages_cloned = 0
    assets_downloaded = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        while to_visit:
            batch = []
            for url, depth in to_visit:
                if url in visited or depth > max_depth:
                    continue
                if respect_robots and not is_allowed(url, base_domain, disallowed):
                    visited.add(url)
                    continue
                visited.add(url)
                batch.append((url, depth))
                if len(batch) >= concurrency:
                    break

            batch_urls = {u for u, _ in batch}
            to_visit = [(u, d) for u, d in to_visit if u not in batch_urls]

            if not batch:
                break

            futures = {
                executor.submit(fetch_url, url): (url, depth)
                for url, depth in batch
            }

            new_pages = []
            new_assets = []

            for future in concurrent.futures.as_completed(futures):
                url, depth = futures[future]
                url, status, ct, text, raw = future.result()

                if status != 200 or not raw:
                    continue

                is_html = "text/html" in ct or (not ct and (text[:15].lower().startswith("<!doctype") or text[:6].lower().startswith("<html")))
                is_css = "text/css" in ct
                is_js = any(ct.startswith(t) for t in ("application/javascript", "text/javascript"))

                fp = url_to_filepath(url, output)
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(raw)

                if is_html:
                    pages_cloned += 1
                    success(f"[page {pages_cloned}] {url}")

                    if depth < max_depth:
                        links = extract_page_links(text, url)
                        for link in links:
                            lp = urlparse(link)
                            if lp.hostname == base_domain and link not in visited:
                                new_pages.append((link, depth + 1))

                    assets = extract_html_assets(text, url)
                    for a in assets:
                        ap = urlparse(a)
                        if ap.hostname == base_domain and a not in visited:
                            new_assets.append(a)

                elif is_css:
                    assets_downloaded += 1
                    css_assets = extract_css_resources(text, url)
                    for a in css_assets:
                        ap = urlparse(a)
                        if ap.hostname == base_domain and a not in visited:
                            new_assets.append(a)

                elif is_js:
                    assets_downloaded += 1
                    js_refs = extract_js_references(text, url)
                    for a in js_refs:
                        ap = urlparse(a)
                        if ap.hostname == base_domain and a not in visited:
                            new_assets.append(a)

                else:
                    assets_downloaded += 1

            for link, d in new_pages:
                to_visit.append((link, d))

            if new_assets:
                asset_batch = [a for a in new_assets if a not in visited][:concurrency * 3]
                af = {
                    executor.submit(fetch_url, a): a
                    for a in asset_batch
                }
                for f in concurrent.futures.as_completed(af):
                    a_url, a_status, a_ct, a_text, a_raw = f.result()
                    visited.add(a_url)
                    if a_status == 200 and a_raw:
                        fp = url_to_filepath(a_url, output)
                        fp.parent.mkdir(parents=True, exist_ok=True)
                        fp.write_bytes(raw if False else a_raw)
                        assets_downloaded += 1

                        if "text/css" in a_ct:
                            css_assets = extract_css_resources(a_text, a_url)
                            for ca in css_assets:
                                cap = urlparse(ca)
                                if cap.hostname == base_domain and ca not in visited:
                                    new_assets.append(ca)

                        if any(a_ct.startswith(t) for t in ("application/javascript", "text/javascript")):
                            js_refs = extract_js_references(a_text, a_url)
                            for jr in js_refs:
                                jrp = urlparse(jr)
                                if jrp.hostname == base_domain and jr not in visited:
                                    new_assets.append(jr)

            if delay > 0:
                time.sleep(delay)

    info(f"Done! {pages_cloned} pages + {assets_downloaded} assets -> {output}")
    return pages_cloned


def register(subs):
    p = subs.add_parser("cloner", help="Clone an entire website")
    p.add_argument("url", help="URL to clone")
    p.add_argument("-o", "--output", default=None,
                   help="Output directory (default: cloned_<domain>)")
    p.add_argument("-d", "--depth", type=int, default=5,
                   help="Max crawl depth (default: 5)")
    p.add_argument("-c", "--concurrency", type=int, default=10,
                   help="Concurrent requests (default: 10)")
    p.add_argument("--no-robots", action="store_true",
                   help="Ignore robots.txt")
    p.add_argument("--delay", type=float, default=0.1,
                   help="Delay between batches (seconds)")
    p.set_defaults(func=cmd)


def cmd(args):
    url = args.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    output = args.output
    if output is None:
        domain = urlparse(url).hostname.replace(".", "_")
        output = str(CLONED_DIR / f"cloned_{domain}")

    info(f"Cloning {url} (depth={args.depth}, concurrency={args.concurrency})")
    try:
        clone_site(url, output, max_depth=args.depth,
                   concurrency=args.concurrency,
                   respect_robots=not args.no_robots,
                   delay=args.delay)
    except KeyboardInterrupt:
        warning("Interrupted")
    except Exception as e:
        error(f"Cloning failed: {e}")
