import concurrent.futures
import json
import sys
from datetime import datetime
from pathlib import Path

from phox.config import success, error, info, OUTPUT_DIR, c, t
from phox.lib.http import get as http_get

PLATFORMS = {
    "twitter":     {"url": "https://x.com/{}",                  "check": lambda r: r.status_code == 404, "icon": "\U0001F426", "cat": "Social"},
    "instagram":   {"url": "https://www.instagram.com/{}/",      "check": lambda r: r.status_code == 404, "icon": "\U0001F4F7", "cat": "Social"},
    "reddit":      {"url": "https://www.reddit.com/user/{}",     "check": lambda r: r.status_code == 404, "icon": "\U0001F916", "cat": "Social"},
    "tiktok":      {"url": "https://www.tiktok.com/@{}",         "check": lambda r: r.status_code == 404, "icon": "\U0001F3B5", "cat": "Social"},
    "youtube":     {"url": "https://www.youtube.com/@{}",        "check": lambda r: r.status_code == 404, "icon": "\U0001F4FA", "cat": "Social"},
    "twitch":      {"url": "https://www.twitch.tv/{}",           "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Social"},
    "pinterest":   {"url": "https://www.pinterest.com/{}/",      "check": lambda r: r.status_code == 404, "icon": "\U0001F4CC", "cat": "Social"},
    "linkedin":    {"url": "https://www.linkedin.com/in/{}",     "check": lambda r: r.status_code == 404, "icon": "\U0001F4BC", "cat": "Social"},
    "medium":      {"url": "https://medium.com/@{}",             "check": lambda r: r.status_code == 404, "icon": "\U0001F4DD", "cat": "Social"},
    "snapchat":    {"url": "https://www.snapchat.com/add/{}",    "check": lambda r: r.status_code == 404, "icon": "\U0001F4F9", "cat": "Social"},
    "facebook":    {"url": "https://www.facebook.com/{}",        "check": lambda r: r.status_code == 404, "icon": "\U0001F310", "cat": "Social"},
    "mastodon":    {"url": "https://mastodon.social/@{}",        "check": lambda r: r.status_code == 404, "icon": "\U0001F434", "cat": "Social"},
    "threads":     {"url": "https://www.threads.net/@{}",        "check": lambda r: r.status_code == 404, "icon": "\U0001F517", "cat": "Social"},
    "bluesky":     {"url": "https://bsky.app/profile/{}.bsky.social",        "check": lambda r: r.status_code == 404, "icon": "\U0001F426", "cat": "Social"},
    "github":      {"url": "https://github.com/{}",              "check": lambda r: r.status_code == 404, "icon": "\U0001F419", "cat": "Developer"},
    "gitlab":      {"url": "https://gitlab.com/{}",              "check": lambda r: r.status_code == 404, "icon": "\U0001F4BB", "cat": "Developer"},
    "bitbucket":   {"url": "https://bitbucket.org/{}/",          "check": lambda r: r.status_code == 404, "icon": "\U0001F4E6", "cat": "Developer"},
    "stackoverflow":{"url": "https://stackoverflow.com/users/?tab=Accounts&ReputationSort=Reputation&ReputationFrom=0&ReputationTo=0&SelectedIds={}", "check": lambda r: r.status_code == 404, "icon": "\U0001F4DA", "cat": "Developer"},
    "deviantart":  {"url": "https://www.deviantart.com/{}",      "check": lambda r: r.status_code == 404, "icon": "\U0001F3A8", "cat": "Developer"},
    "npm":         {"url": "https://www.npmjs.com/~{}",          "check": lambda r: r.status_code == 404, "icon": "\U0001F4E6", "cat": "Developer"},
    "pypi":        {"url": "https://pypi.org/user/{}/",          "check": lambda r: r.status_code == 404, "icon": "\U0001F40D", "cat": "Developer"},
    "codepen":     {"url": "https://codepen.io/{}",              "check": lambda r: r.status_code == 404, "icon": "\u270F", "cat": "Developer"},
    "replit":      {"url": "https://replit.com/@{}",             "check": lambda r: r.status_code == 404, "icon": "\U0001F525", "cat": "Developer"},
    "keybase":     {"url": "https://keybase.io/{}",              "check": lambda r: r.status_code == 404, "icon": "\U0001F511", "cat": "Developer"},
    "steam(down)":       {"url": "https://steamcommunity.com/id/{}",   "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Gaming"},
    "roblox":      {"url": "https://www.roblox.com/user.aspx?username={}", "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Gaming"},
    "xbox":        {"url": "https://www.xbox.com/en-us/play/user/{}", "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Gaming"},
    "playstation": {"url": "https://psnprofiles.com/{}",         "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Gaming"},
    "epicgames":   {"url": "https://www.epicgames.com/site/en-US/u/{}", "check": lambda r: r.status_code == 404, "icon": "\U0001F3AE", "cat": "Gaming"},
    "spotify":     {"url": "https://open.spotify.com/user/{}",   "check": lambda r: r.status_code == 404, "icon": "\U0001F3B5", "cat": "Media"},
    "soundcloud":  {"url": "https://soundcloud.com/{}",          "check": lambda r: r.status_code == 404, "icon": "\U0001F3B5", "cat": "Media"},
    "vimeo":       {"url": "https://vimeo.com/{}",               "check": lambda r: r.status_code == 404, "icon": "\U0001F3AC", "cat": "Media"},
    "flickr":      {"url": "https://www.flickr.com/people/{}",   "check": lambda r: r.status_code == 404, "icon": "\U0001F4F7", "cat": "Media"},
    "tumblr":      {"url": "https://{}.tumblr.com",              "check": lambda r: r.status_code == 404, "icon": "\U0001F4F0", "cat": "Media"},
    "behance":     {"url": "https://www.behance.net/{}",         "check": lambda r: r.status_code == 404, "icon": "\U0001F4A8", "cat": "Media"},
    "telegram":    {"url": "https://t.me/{}",                    "check": lambda r: r.status_code == 404, "icon": "\U0001F4E9", "cat": "Chat"},
    "discord (down)":     {"url": "https://discord.com",                "check": lambda r: False, "icon": "\U0001F3AE", "cat": "Chat", "note": "Cannot check"},
    "slack":       {"url": "https://{}.slack.com",               "check": lambda r: r.status_code == 404, "icon": "\U0001F4AC", "cat": "Chat"},
    "pastebin":    {"url": "https://pastebin.com/u/{}",          "check": lambda r: r.status_code == 404, "icon": "\U0001F4CB", "cat": "Other"},
    "hackerone":   {"url": "https://hackerone.com/{}",           "check": lambda r: r.status_code == 404, "icon": "\U0001F41B", "cat": "Other"},
    "etsy":        {"url": "https://www.etsy.com/people/@{}",    "check": lambda r: r.status_code == 404, "icon": "\U0001F4E6", "cat": "Other"},
    "gravatar":    {"url": "https://en.gravatar.com/{}",         "check": lambda r: r.status_code == 404, "icon": "\U0001F464", "cat": "Other"},
}


def check_one(pname, pconfig, username):
    url = pconfig["url"].format(username)
    try:
        resp = http_get(url, timeout=10,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                        allow_redirects=False)
        return {
            "platform": pname, "available": pconfig["check"](resp),
            "url": url, "icon": pconfig.get("icon", ""),
            "category": pconfig.get("cat", "Other"),
        }
    except Exception as e:
        return {
            "platform": pname, "available": None,
            "url": url, "icon": pconfig.get("icon", ""),
            "category": pconfig.get("cat", "Other"),
            "error": str(e),
        }


def register(subs):
    p = subs.add_parser("username",
                        help="Check username availability across platforms")
    p.add_argument("name", help="Username to check")
    p.add_argument("-p", "--platform", dest="platforms", nargs="+",
                   help="Platforms to check (default: all)")
    p.add_argument("-o", "--output", default=None,
                   help="Save result to file")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.set_defaults(func=cmd)


def _bold(text):
    return c(text, "bold")


def _primary(text):
    return c(text, "primary")


def _muted(text):
    return c(text, "muted")


def _check_available(platform, icon, url):
    theme = t()
    return (
        f"  {theme['bold']}{theme['success']}\u2714{theme['reset']} "
        f"{icon} {platform:>18s}  "
        f"{theme['success']}AVAILABLE{theme['reset']}  "
        f"{_muted(url)}"
    )


def _check_taken(platform, icon, url):
    theme = t()
    return (
        f"  {theme['bold']}{theme['error']}\u2718{theme['reset']} "
        f"{icon} {platform:>18s}  "
        f"{theme['error']}TAKEN{theme['reset']}{theme['muted']}{theme['reset']}      "
        f"{_muted(url)}"
    )


def _check_unknown(platform, icon, note):
    theme = t()
    return (
        f"  {theme['bold']}{theme['warning']}\u003F{theme['reset']} "
        f"{icon} {platform:>18s}  "
        f"{theme['warning']}UNKNOWN{theme['reset']}   "
        f"{_muted(note)}"
    )


def cmd(args):
    info(f"Checking username '{args.name}' across platforms...")

    if args.platforms:
        cp = {p: PLATFORMS[p] for p in args.platforms if p in PLATFORMS}
        if not cp:
            error(f"Invalid platforms. Available: {', '.join(sorted(PLATFORMS.keys()))}")
            return
    else:
        cp = PLATFORMS

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        futs = {ex.submit(check_one, n, c, args.name): n for n, c in cp.items()}
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
    results.sort(key=lambda x: x["platform"])

    avail_list = [r["platform"] for r in results if r.get("available")]
    taken_list = [r["platform"] for r in results if not r.get("available") and not r.get("error")]
    save_data = {
        "username": args.name,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "available": len(avail_list),
            "taken": len(taken_list),
            "errors": len(results) - len(avail_list) - len(taken_list),
            "total": len(results),
        },
        "available_on": avail_list,
        "taken_on": taken_list,
        "results": results,
    }

    save_dir = OUTPUT_DIR / "username"
    save_dir.mkdir(parents=True, exist_ok=True)
    auto_path = save_dir / f"{args.name}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(auto_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    info(f"Auto-saved to {auto_path}")

    # Custom output
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        success(f"Saved to {out}")

    if args.as_json:
        print(json.dumps(save_data, indent=2))
        return

    theme = t()

    print()
    print(f"  {_bold(theme['primary'] + '═══════════════════════════════════════════════════════' + theme['reset'])}")
    print(f"  {_bold(_primary(f'  USERNAME RESULTS: {args.name}'))}")
    print(f"  {_bold(theme['primary'] + '═══════════════════════════════════════════════════════' + theme['reset'])}")

    avail = taken = errs = 0
    current_cat = None
    for r in results:
        cat = r.get("category", "Other")
        if cat != current_cat:
            current_cat = cat
            print()
            print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")
            print(f"  {_bold(_primary(f'  {cat.upper()}'))}")
            print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")

        icon = r.get("icon", "")
        plat = r["platform"].title()

        if r.get("error"):
            print(_check_unknown(plat, icon, r.get("note", r["error"][:50])))
            errs += 1
        elif r["available"]:
            print(_check_available(plat, icon, r["url"]))
            avail += 1
        else:
            print(_check_taken(plat, icon, r["url"]))
            taken += 1

    print()
    print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")
    print(
        f"  {theme['success']}{theme['bold']}{avail} available{theme['reset']}  "
        f"{theme['muted']}|{theme['reset']}  "
        f"{theme['error']}{theme['bold']}{taken} taken{theme['reset']}  "
        f"{theme['muted']}|{theme['reset']}  "
        f"{theme['warning']}{theme['bold']}{errs} unknown{theme['reset']}  "
        f"{theme['muted']}|{theme['reset']}  "
        f"{theme['muted']}{len(results)} total{theme['reset']}"
    )
    print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")
    print()
