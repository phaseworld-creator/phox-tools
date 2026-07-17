import json
from datetime import datetime

from phox.config import PHOX_DIR, success, error, info
from phox.lib.http import request as http_request

WEBHOOKS_FILE = PHOX_DIR / "webhooks.json"
HISTORY_FILE = PHOX_DIR / "webhook_history.json"


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return [] if "history" in str(path) else []


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def register(subs):
    wh = subs.add_parser("webhook", help="Manage and send webhooks")
    wh_sub = wh.add_subparsers(dest="subcmd")
    p = wh_sub.add_parser("send", help="Send a webhook")
    p.add_argument("url")
    p.add_argument("-d", "--data", default=None)
    p.add_argument("--method", default="POST",
                   choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    p.add_argument("-H", "--header", dest="headers", nargs="+", default=[])
    p.add_argument("--name", default=None, help="Save as named webhook")
    p.set_defaults(func=cmd_send)
    p = wh_sub.add_parser("discord", help="Send a message to a Discord webhook")
    p.add_argument("url", help="Discord webhook URL")
    p.add_argument("-m", "--message", required=True, help="Message text")
    p.add_argument("-t", "--title", default=None, help="Embed title")
    p.add_argument("-c", "--color", default=None, help="Embed color (hex, e.g. 0xff0000)")
    p.add_argument("-i", "--image", default=None, help="Image URL for embed")
    p.add_argument("--username", default=None, help="Override bot username")
    p.add_argument("--avatar", default=None, help="Override bot avatar URL")
    p.set_defaults(func=cmd_discord)
    p = wh_sub.add_parser("list", help="List saved webhooks")
    p.set_defaults(func=cmd_list)
    p = wh_sub.add_parser("fire", help="Fire a saved webhook by name")
    p.add_argument("name")
    p.add_argument("-d", "--data", default=None)
    p.set_defaults(func=cmd_fire)
    p = wh_sub.add_parser("history", help="Show webhook history")
    p.set_defaults(func=cmd_history)

    wh.set_defaults(func=cmd_webhook_help)


def cmd_webhook_help(args):
    from phox.config import t
    theme = t()
    b = theme.get("bold", "")
    r = theme.get("reset", "")
    c = theme.get("primary", "")
    m = theme.get("muted", "")

    print(f"""
{c}{b}  Webhook Manager{r}
  Send and manage webhooks from the terminal

{b}  Usage:{r}
    phox webhook <command> [options]

{b}  Commands:{r}
    send <url>              Send a webhook to any URL
    discord <url>           Send a Discord message
    list                    List saved webhooks
    fire <name>             Fire a saved webhook by name
    history                 Show recent webhook history

{b}  Discord Examples:{r}
{m}  Send a simple message:{r}
    phox webhook discord https://discord.com/api/webhooks/ID/TOKEN -m "Hello World"

{m}  Send an embed with title and color:{r}
    phox webhook discord <url> -m "Server started" -t "Alert" -c 0xff0000

{m}  Send with image:{r}
    phox webhook discord <url> -m "Check this out" -i "https://example.com/img.png"

{m}  Custom username:{r}
    phox webhook discord <url> -m "Hey" --username "Phox Bot"

{b}  Generic Examples:{r}
{m}  Send JSON to any webhook:{r}
    phox webhook send <url> -d '{{"content": "Hello"}}'

{m}  Send and save for later:{r}
    phox webhook send <url> -d '{{"text":"hi"}}' --name my-hook
    phox webhook fire my-hook
""")


def cmd_discord(args):
    url = args.url
    if not "discord.com/api/webhooks" in url and not "discordapp.com/api/webhooks" in url:
        error("URL does not look like a Discord webhook URL")
        print(f"    {url}")
        return

    # Build the embed
    embed = {}
    if args.title:
        embed["title"] = args.title
    embed["description"] = args.message
    if args.color:
        try:
            embed["color"] = int(args.color, 16) if args.color.startswith("0x") else int(args.color)
        except ValueError:
            error(f"Invalid color: {args.color} (use hex like 0xff0000)")
            return
    if args.image:
        embed["image"] = {"url": args.image}

    payload = {"embeds": [embed]}
    if args.username:
        payload["username"] = args.username
    if args.avatar:
        payload["avatar_url"] = args.avatar

    headers = {"Content-Type": "application/json"}

    info(f"Sending Discord webhook...")
    try:
        resp = http_request("POST", url, headers=headers,
                            json_body=payload, timeout=10)
        if resp.status_code in (200, 204):
            success(f"Message sent! (HTTP {resp.status_code})")
        else:
            error(f"Discord returned HTTP {resp.status_code}")
            if resp.text:
                print(f"    {resp.text[:300]}")
    except Exception as e:
        error(f"Failed: {e}")
        return

    history = load_json(HISTORY_FILE)
    if not isinstance(history, list):
        history = []
    history.append({
        "url": url, "method": "POST",
        "status": resp.status_code,
        "timestamp": datetime.now().isoformat(),
        "type": "discord",
    })
    save_json(HISTORY_FILE, history[-100:])


def cmd_send(args):
    headers = {"Content-Type": "application/json"}
    for h in args.headers:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    payload = None
    if args.data:
        try:
            payload = json.loads(args.data)
        except json.JSONDecodeError:
            payload = {"data": args.data}

    info(f"Sending {args.method} webhook to {args.url}")
    try:
        resp = http_request(args.method, args.url, headers=headers,
                            json_body=payload, timeout=10)
        sc = resp.status_code
        success(f"Response: {sc}")
        if resp.text:
            print(f"  Body: {resp.text[:500]}")
    except Exception as e:
        error(f"Failed: {e}")
        return

    history = load_json(HISTORY_FILE)
    if not isinstance(history, list):
        history = []
    history.append({
        "url": args.url, "method": args.method,
        "status": sc, "timestamp": datetime.now().isoformat(),
    })
    save_json(HISTORY_FILE, history[-100:])

    if args.name:
        webhooks = load_json(WEBHOOKS_FILE)
        if not isinstance(webhooks, list):
            webhooks = []
        webhooks.append({
            "name": args.name, "url": args.url, "method": args.method,
            "headers": headers, "created": datetime.now().isoformat(),
        })
        save_json(WEBHOOKS_FILE, webhooks)
        success(f"Saved as '{args.name}'")


def cmd_list(args):
    webhooks = load_json(WEBHOOKS_FILE)
    if not webhooks:
        info("No saved webhooks. Use 'phox webhook send --name <name>' to save one.")
        return
    print()
    for i, w in enumerate(webhooks, 1):
        print(f"  {i}. {w['name']}")
        print(f"     URL: {w['url']}")
        print(f"     Method: {w.get('method', 'POST')}")
    print()


def cmd_fire(args):
    webhooks = load_json(WEBHOOKS_FILE)
    wh = next((w for w in webhooks if w["name"] == args.name), None)
    if not wh:
        error(f"Webhook '{args.name}' not found")
        return

    payload = None
    if args.data:
        try:
            payload = json.loads(args.data)
        except json.JSONDecodeError:
            payload = {"data": args.data}

    info(f"Firing '{args.name}'...")
    try:
        resp = http_request(wh.get("method", "POST"), wh["url"],
                            headers=wh.get("headers", {}),
                            json_body=payload, timeout=10)
        success(f"Response: {resp.status_code}")
    except Exception as e:
        error(f"Failed: {e}")


def cmd_history(args):
    history = load_json(HISTORY_FILE)
    if not history:
        info("No history yet.")
        return
    print()
    for entry in history[-20:]:
        sc = entry["status"]
        print(f"  {entry['timestamp']}  {entry['method']:>6}  {sc}  {entry['url']}")
    print()
