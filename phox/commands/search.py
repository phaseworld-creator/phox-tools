import json as json_mod

from phox.config import error, info
from phox.lib.http import post as http_post
from phox.lib.html import extract_links

DDG_URL = "https://html.duckduckgo.com/html/"


def search_ddg(query, max_results=10):
    results = []
    try:
        resp = http_post(
            DDG_URL,
            data="q=" + query,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
    except Exception as e:
        error(f"Search failed: {e}")
        return results

    import re
    blocks = re.split(r'<div class="result[^"]*">', resp.text)
    for block in blocks[1:max_results + 1]:
        title_m = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_m = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
        url_m = re.search(r'class="result__url"[^>]*>(.*?)</a>', block, re.DOTALL)

        if title_m:
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
            url = ""
            href_m = re.search(r'href="([^"]+)"', title_m.group(0))
            if href_m:
                url = href_m.group(1)
            snippet = ""
            if snippet_m:
                snippet = re.sub(r"<[^>]+>", "", snippet_m.group(1)).strip()
            display_url = ""
            if url_m:
                display_url = re.sub(r"<[^>]+>", "", url_m.group(1)).strip()

            results.append({
                "title": title,
                "url": url,
                "display_url": display_url or url,
                "snippet": snippet,
            })

    return results


def register(subs):
    p = subs.add_parser("search", help="Search the web via DuckDuckGo")
    p.add_argument("query", help="Search query")
    p.add_argument("-n", "--max-results", type=int, default=10,
                   help="Max results (default: 10)")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.set_defaults(func=cmd)


def cmd(args):
    info(f"Searching for: {args.query}")
    results = search_ddg(args.query, args.max_results)

    if not results:
        error("No results found.")
        return

    if args.as_json:
        print(json_mod.dumps(results, indent=2))
        return

    for i, r in enumerate(results, 1):
        print()
        print(f"  {i}. {r['title']}")
        print(f"     {r['display_url']}")
        if r["snippet"]:
            print(f"     {r['snippet']}")
    print()
