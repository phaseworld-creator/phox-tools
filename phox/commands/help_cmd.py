"""Custom detailed help command for Phox Tools."""

import sys

from phox import __version__
from phox.config import c, t, banner

COMMANDS = {
    "encode": {
        "group": "Encoding",
        "usage": "phox encode <base64|hex|url> <text>",
        "desc": "Encode text into various formats",
        "examples": [
            'phox encode base64 "Hello World"',
            'phox encode hex "secret"',
            'phox encode url "hello world"',
        ],
    },
    "decode": {
        "group": "Encoding",
        "usage": "phox decode <base64|hex|url> <text>",
        "desc": "Decode encoded text back to original",
        "examples": [
            'phox decode base64 "SGVsbG8="',
            'phox decode hex "48656c6c6f"',
            'phox decode url "hello%20world"',
        ],
    },
    "hash": {
        "group": "Encoding",
        "usage": 'phox hash <text> [-a ALGO]',
        "desc": "Hash text with cryptographic algorithms",
        "options": "  -a, --algo    Algorithm: md5, sha1, sha256 (default), sha512, blake2b, blake2s",
        "examples": [
            'phox hash "password123"',
            'phox hash "data" -a md5',
        ],
    },
    "hash-all": {
        "group": "Encoding",
        "usage": "phox hash-all <text>",
        "desc": "Hash text with ALL algorithms at once",
        "examples": ['phox hash-all "test"'],
    },
    "hash-file": {
        "group": "Encoding",
        "usage": "phox hash-file <file> [-a ALGO] [--all] [-r]",
        "desc": "Hash a file or directory",
        "options": "  -a, --algo    Algorithm (default: sha256)\n  --all         Hash with all algorithms\n  -r, --recursive  Hash all files in directory",
        "examples": [
            "phox hash-file myfile.txt",
            "phox hash-file myfile.txt --all",
            "phox hash-file ./folder -r",
        ],
    },
    "password": {
        "group": "Encoding",
        "usage": "phox password [-l LEN] [-n COUNT]",
        "desc": "Generate cryptographically secure random passwords",
        "options": "  -l, --length      Password length (default: 16)\n  -n, --count       Number of passwords (default: 1)\n  --no-special       No special characters\n  --no-digits        No digits\n  --no-upper         No uppercase",
        "examples": [
            "phox password",
            "phox password -l 32 -n 5",
            "phox password -l 20 --no-special",
        ],
    },
    "rand": {
        "group": "Encoding",
        "usage": "phox rand [-t TYPE] [-n COUNT] [-l LENGTH]",
        "desc": "Generate random data (strings, numbers, UUIDs, IPs, etc.)",
        "options": "  -t, --type     string (default), number, hex, bytes, uuid, ip, password, dice, coin, choice\n  -n, --count    Number of items (default: 1)\n  -l, --length   Length for string/hex/bytes (default: 16)\n  --min, --max   Range for number type\n  --sides        Dice sides (default: 6)\n  --options      Choices for choice type",
        "examples": [
            "phox rand",
            "phox rand -t uuid -n 5",
            "phox rand -t password -l 32",
            "phox rand -t dice -n 3",
            "phox rand -t coin",
            "phox rand -t choice --options red green blue",
        ],
    },
    "cloner": {
        "group": "Web",
        "usage": "phox cloner <url> [options]",
        "desc": "Clone an entire website with depth control and concurrency",
        "options": "  -o, --output        Output directory (default: ~/.phox/output/cloned/)\n  -d, --depth         Max crawl depth (default: 5)\n  -c, --concurrency   Concurrent requests (default: 10)\n  --no-robots         Ignore robots.txt\n  --delay             Delay between batches (seconds)",
        "examples": [
            "phox cloner https://example.com",
            "phox cloner https://site.com -d 3 -o mysite",
        ],
    },
    "search": {
        "group": "Web",
        "usage": 'phox search <query> [-n MAX] [--json]',
        "desc": "Search the web via DuckDuckGo",
        "examples": [
            'phox search "python tutorials"',
            'phox search "hacking tools" -n 5',
        ],
    },
    "api": {
        "group": "Web",
        "usage": "phox api <url> [-X METHOD] [-d BODY]",
        "desc": "Make HTTP API requests",
        "options": "  -X, --method    GET, POST, PUT, PATCH, DELETE (default: GET)\n  -H, --header    Headers as 'Key: Value' (repeatable)\n  -d, --data      Request body (JSON or string)\n  -o, --output    Save response to file\n  -v, --verbose   Show full response headers",
        "examples": [
            "phox api https://api.github.com/users/octocat",
            'phox api https://api.example.com/data -X POST -d \'{"key":"val"}\'',
        ],
    },
    "qr": {
        "group": "Web",
        "usage": 'phox qr <text> [--format svg|txt|pbm] [-o FILE]',
        "desc": "Generate QR codes from text or URLs",
        "options": "  --format    Output: svg (default), txt (terminal art), pbm\n  -o, --output  Output file (saved to ~/.phox/output/)\n  -s, --size   Module size in pixels (default: 10)",
        "examples": [
            'phox qr "https://github.com"',
            'phox qr "WiFi:pass123" --format txt',
            'phox qr "link" -o code.svg',
        ],
    },
    "subdomain": {
        "group": "Recon",
        "usage": "phox subdomain <domain> [-w WORDLIST] [--dns-only]",
        "desc": "Enumerate subdomains via DNS and HTTP probing",
        "options": "  -w, --wordlist   Custom wordlist file\n  --dns-only       Only check DNS, skip HTTP\n  -c, --concurrency  Threads (default: 20)",
        "examples": [
            "phox subdomain example.com",
            "phox subdomain target.com -w mywordlist.txt",
            "phox subdomain target.com --dns-only",
        ],
    },
    "portscan": {
        "group": "Recon",
        "usage": "phox portscan <host> [-p PORTS] [-t TIMEOUT]",
        "desc": "Scan ports on a target host",
        "options": "  -p, --ports       Ports: '80,443' or '1-1000' or 'top100' (default: top20)\n  -t, --timeout     Connection timeout (default: 1.0s)\n  -c, --concurrency  Max threads (default: 50)\n  -v, --verbose     Show closed ports",
        "examples": [
            "phox portscan 192.168.1.1",
            "phox portscan example.com -p 80,443,8080",
            "phox portscan 10.0.0.1 -p 1-1000",
            "phox portscan target.com -p top100",
        ],
    },
    "ip-lookup": {
        "group": "Recon",
        "usage": "phox ip-lookup [IP] [--json]",
        "desc": "Full IP geolocation with security flags",
        "examples": [
            "phox ip-lookup",
            "phox ip-lookup 8.8.8.8",
            "phox ip-lookup 1.1.1.1 --json",
        ],
    },
    "dns": {
        "group": "Recon",
        "usage": "phox dns <domain> [-t TYPE] [--all-types]",
        "desc": "Resolve DNS records for a domain",
        "options": "  -t, --type      Record: A (default), AAAA, MX, NS, TXT, CNAME, SOA\n  --all-types     Query all record types",
        "examples": [
            "phox dns google.com",
            "phox dns google.com -t MX",
            "phox dns example.com --all-types",
        ],
    },
    "whois": {
        "group": "Recon",
        "usage": "phox whois <domain> [--json]",
        "desc": "WHOIS/RDAP domain registration lookup",
        "examples": [
            "phox whois google.com",
            "phox whois example.org --json",
        ],
    },
    "username": {
        "group": "Recon",
        "usage": 'phox username <name> [-p github twitter ...]',
        "desc": "Check username availability across 40+ platforms",
        "options": "  -p, --platform    Platforms to check (default: all)\n                    Social: twitter, instagram, reddit, tiktok, youtube,\n                      twitch, pinterest, linkedin, medium, snapchat,\n                      facebook, threads, bluesky, mastodon\n                    Dev: github, gitlab, bitbucket, deviantart, npm,\n                      pypi, codepen, replit, keybase\n                    Gaming: steam, roblox, epicgames\n                    Media: spotify, soundcloud, vimeo, flickr\n                    Chat: telegram, slack\n                    Other: pastebin, hackerone, gravatar",
        "examples": [
            "phox username john_doe",
            'phox username coolname -p github twitter reddit',
            'phox username hacker -p github gitlab npm keybase',
        ],
    },
    "obfuscate": {
        "group": "Security",
        "usage": "phox obfuscate <file.py> [-o OUT] [-l LAYERS]",
        "desc": "Obfuscate Python code with string encryption and junk code injection",
        "options": "  -o, --output    Output file (saved to ~/.phox/output/)\n  -l, --layers    Encryption layers (default: 1, max: 5)\n  --no-junk       Skip junk code insertion",
        "examples": [
            "phox obfuscate script.py",
            "phox obfuscate script.py -o protected.py -l 3",
        ],
    },
    "colors": {
        "group": "Utilities",
        "usage": "phox colors [--test]",
        "desc": "Display terminal color palette and test color support",
        "examples": [
            "phox colors",
            "phox colors --test",
        ],
    },
    "webhook": {
        "group": "Utilities",
        "usage": "phox webhook <send|discord|list|fire|history>",
        "desc": "Send and manage webhooks (including Discord)",
        "subcommands": [
            "  send <url> [-d DATA] [--name NAME]  Send a webhook",
            "  discord <url> -m MSG                 Send a Discord embed message",
            "  list                                List saved webhooks",
            "  fire <name> [-d DATA]                Fire a saved webhook",
            "  history                             Show send history",
        ],
        "examples": [
            "phox webhook discord https://discord.com/api/webhooks/ID/TOKEN -m 'Hello'",
            "phox webhook discord <url> -m 'Alert!' -t 'Title' -c 0xff0000",
            "phox webhook send <url> -d '{\"msg\":\"hi\"}'",
            "phox webhook fire my-hook",
        ],
    },
    "theme": {
        "group": "Utilities",
        "usage": "phox theme <list|set|preset|show|create|reset>",
        "desc": "Customize Phox terminal appearance",
        "subcommands": [
            "  list                         List available themes",
            "  set <name>                   Set active theme",
            "  preset <name>                Apply preset: hacker, ocean, sunset, matrix, cyberpunk",
            "  show [name]                  Show theme colors",
            "  create <name>                Create custom theme interactively",
            "  reset                        Reset to default",
        ],
        "examples": [
            "phox theme preset matrix",
            "phox theme list",
            "phox theme create mytheme",
        ],
    },
    "custom": {
        "group": "Utilities",
        "usage": "phox custom <new|list|run|edit|delete|share>",
        "desc": "Create and manage your own custom commands",
        "subcommands": [
            "  new <name> [-d DESC]     Create a new custom command",
            "  list                     List all custom commands",
            "  run <name> [args...]     Run a custom command",
            "  edit <name>              Open command file for editing",
            "  delete <name>            Delete a custom command",
            "  share                    Show how to share commands",
        ],
        "examples": [
            'phox custom new my-tool -d "My awesome tool"',
            "phox custom list",
            "phox custom run my-tool",
        ],
    },
    "web": {
        "group": "Utilities",
        "usage": "phox web [port]",
        "desc": "Start the web UI in your browser",
        "options": "  port    Port number (default: 1234)",
        "examples": [
            "phox web",
            "phox web 3000",
        ],
    },
    "banner": {
        "group": "Utilities",
        "usage": "phox banner",
        "desc": "Display the PHOX ASCII art banner",
        "examples": ["phox banner"],
    },
}


def register(subs):
    pass


def cmd(args):
    cmd_arg = getattr(args, "command_arg", None)
    if cmd_arg:
        show_command_help(cmd_arg)
    else:
        show_full_help()

CATEGORY_COLORS = {
    "Encoding": "info",
    "Web": "primary",
    "Recon": "warning",
    "Security": "error",
    "Utilities": "success",
}


def _dim(text):
    return c(text, "muted")


def _primary(text):
    return c(text, "primary")


def _bold(text):
    return c(text, "bold")


def _success(text):
    return c(text, "success")


def _error(text):
    return c(text, "error")


def _warning(text):
    return c(text, "warning")


def _info(text):
    return c(text, "info")


def _section_line():
    theme = t()
    return f"{theme['muted']}{'─' * 60}{theme['reset']}"


def _thick_line():
    theme = t()
    return f"{theme['muted']}{'═' * 60}{theme['reset']}"


def show_command_help(name):
    info = COMMANDS.get(name)
    if not info:
        for k in COMMANDS:
            if k.replace("-", "") == name.replace("-", ""):
                info = COMMANDS[k]
                name = k
                break

    if not info:
        print()
        print(f"  {_error('Unknown command:')} {name}")
        print(f"  {_dim('Run')} {_bold('phox help')} {_dim('to see all commands')}")
        print()
        return

    group = info.get("group", "")
    cat_color = CATEGORY_COLORS.get(group, "info")

    print()
    print(f"  {_thick_line()}")
    print(f"  {_bold(c(group.upper(), cat_color))}  {_primary(name)}")
    print(f"  {_thick_line()}")
    print()
    print(f"  {c(info['desc'], 'muted')}")
    print()
    print(f"  {_bold('Usage:')}")
    print(f"    {_info(info['usage'])}")
    print()

    if "options" in info:
        print(f"  {_bold('Options:')}")
        for line in info["options"].split("\n"):
            print(f"    {line}")
        print()

    if "subcommands" in info:
        print(f"  {_bold('Subcommands:')}")
        for line in info["subcommands"]:
            print(f"    {line}")
        print()

    if "examples" in info:
        print(f"  {_bold('Examples:')}")
        for ex in info["examples"]:
            print(f"    {_success('$')} {ex}")
        print()


TIPS = [
    ("Combine encode + hash:", 'phox hash "$(phox encode base64 "secret")"'),
    ("Quick recon sweep:", "phox ip-lookup && phox dns target.com"),
    ("Check all username handles:", 'phox username myname -p github twitter'),
    ("Generate + save QR:", 'phox qr "https://example.com" -o link.svg'),
    ("Full port scan:", "phox portscan target.com -p 1-65535"),
    ("Batch hash file:", "phox hash-file ./project --all -r"),
]


def show_full_help():
    banner()

    groups = {}
    for name, info in COMMANDS.items():
        g = info.get("group", "Other")
        if g not in groups:
            groups[g] = []
        groups[g].append((name, info))

    order = ["Encoding", "Web", "Recon", "Security", "Utilities"]
    for group in order:
        if group not in groups:
            continue
        cmds = groups[group]
        cat_color = CATEGORY_COLORS.get(group, "info")

        print(f"  {_dim('─' * 60)}")
        print(f"  {_bold(c(f'  {group.upper()}', cat_color))}")
        print(f"  {_dim('─' * 60)}")

        for name, info in cmds:
            desc = info["desc"]
            print(f"    {_primary(name):<24s} {_dim(desc)}")
        print()

    print(f"  {_dim('─' * 60)}")
    print(f"  {_bold(c('  TIPS', 'warning'))}")
    print(f"  {_dim('─' * 60)}")
    for label, combo in TIPS:
        print(f"    {_dim(label)}")
        print(f"      {_info('$')} {_bold(combo)}")
    print()

    print(f"  {_dim('─' * 60)}")
    print(
        f"  {_dim(f'v{__version__}')}"
        f"  {_dim('|')}"
        f"  {_dim('Zero dependencies')}"
        f"  {_dim('|')}"
        f"  {_dim('Pure Python')}"
    )
    print(
        f"  {_dim('Run')}"
        f"  {_bold('phox help <command>')}"
        f"  {_dim('for detailed usage and examples')}"
    )
    print()
