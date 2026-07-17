import concurrent.futures
import itertools
import json
import socket
import sys
from pathlib import Path
from phox.config import success, error, info, warning, OUTPUT_DIR
from phox.lib.http import get as http_get

COMMON_SUBDOMAINS = [
    "www", "mail", "smtp", "pop", "pop3", "imap", "webmail", "mx", "mx1", "mx2", "mx3",
    "ns1", "ns2", "ns3", "ns4", "ns5", "dns", "dns1", "dns2",
    "ftp", "sftp", "ssh", "telnet", "vpn", "remote", "gateway",
    "api", "dev", "development", "staging", "stage", "test", "testing", "qa", "uat",
    "sandbox", "preprod", "pre-production", "preview", "canary", "nightly",
    "ci", "cd", "jenkins", "travis", "gitlab", "github", "drone", "circle",
    "docker", "k8s", "kubernetes", "swarm", "rancher", "registry",
    "git", "gitlab", "bitbucket", "gogs", "gitea", "svn", "stash",
    "sonar", "nexus", "artifactory", "jfrog", "harbor", "mirror",
    "grafana", "prometheus", "kibana", "elastic", "elasticsearch", "logstash",
    "datadog", "sentry", "newrelic", "statuspage", "uptime", "health",
    "admin", "administrator", "panel", "cpanel", "whm", "webmin", "plesk",
    "cp", "login", "signin", "auth", "oauth", "sso", "id", "identity",
    "portal", "dashboard", "manage", "management", "console", "root",
    "db", "database", "mysql", "mariadb", "postgres", "postgresql", "psql",
    "redis", "redis6", "redis7", "mongo", "mongodb", "mongo0",
    "memcache", "memcached", "cassandra", "couchdb", "influxdb",
    "neo4j", "couchbase", "dynamodb",
    "rabbitmq", "kafka", "kafka0", "kafka1", "activemq",
    "nats", "celery", "worker", "queue",
    "cdn", "static", "assets", "media", "img", "images", "image",
    "video", "videos", "upload", "uploads", "files", "file", "download",
    "downloads", "content", "resources", "public", "private",
    "storage", "s3", "bucket", "blob", "store", "shop",
    "aws", "ec2", "lambda", "azure", "gcp", "google", "cloud",
    "cloudflare", "akamai", "fastly", "cloudfront", "edge", "origin",
    "heroku", "vercel", "netlify", "firebase", "appspot",
    "app", "web", "site", "www2", "www3", "www4", "www5",
    "beta", "alpha", "demo", "preview", "live", "production", "prod",
    "old", "new", "archive", "legacy", "classic", "next",
    "v2", "v3", "v4", "v5",
    "blog", "news", "forum", "community", "wiki", "help", "support",
    "docs", "doc", "documentation", "kb", "faq", "learn", "academy",
    "shop", "store", "commerce", "checkout", "pay", "payment", "payments",
    "cart", "billing", "invoice", "merchant", "affiliate", "partners",
    "order", "orders", "catalog", "product", "products", "marketplace",
    "mail2", "email", "newsletter", "campaign", "marketing", "promo",
    "analytics", "stats", "statistics", "metrics", "tracking",
    "chat", "messaging", "msg", "message", "messages", "talk", "call",
    "voip", "sip", "phone", "sms", "push", "notify",
    "secure", "security", "ssl", "tls", "cert", "certs",
    "owa", "exchange", "autodiscover", "autoconfig",
    "firewall", "waf", "scan", "pentest",
    "intranet", "internal", "private", "corp", "corporate", "office",
    "hr", "crm", "erp", "jira", "confluence", "bamboo", "trello",
    "vpn2", "rdp", "bastion", "jump", "tunnel", "proxy", "squid",
    "api2", "api3", "api-v1", "api-v2", "api-v3", "rest", "graphql",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "01", "02", "03", "04", "05", "100", "200", "300",
    "us", "uk", "eu", "de", "fr", "es", "it", "nl", "au", "ca",
    "jp", "cn", "in", "br", "ru", "sg", "hk",
    "m", "mobile", "touch", "wap", "lite", "amp", "pwa",
    "link", "links", "redirect", "go", "r",
    "pic", "pics", "photo", "photos", "thumb", "thumbs",
    "asset", "res", "dist", "build", "bundle",
    "node", "server", "server1", "server2", "host",
    "backup", "backups", "bak", "tmp", "temp", "cache",
    "log", "logs", "error", "debug",
    "monitor", "monitoring",
    "status", "ping", "heartbeat",
    "data", "warehouse", "lake",
    "hadoop", "hive", "spark", "superset", "metabase",
]

_WORDLIST_URLS = [
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt",
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-20000.txt",
    "https://raw.githubusercontent.com/rez0/subdomains/main/subdomains.txt",
    "https://raw.githubusercontent.com/appsecco/bug-bounty-wordlists/master/subdomains.txt",
]

_WORDLIST_CACHE = Path.home() / ".phox" / "wordlists"


def download_large_wordlist():
    import urllib.request as _ur
    import time as _t
    _WORDLIST_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = _WORDLIST_CACHE / "subdomains.txt"

    if cache_file.exists():
        age = _t.time() - cache_file.stat().st_mtime
        if age < 86400:
            try:
                words = cache_file.read_text(encoding="utf-8", errors="replace").splitlines()
                words = [w.strip().lower() for w in words if w.strip() and not w.startswith("#") and w.strip().isascii()]
                if words:
                    return words
            except Exception:
                pass

    for url in _WORDLIST_URLS:
        try:
            req = _ur.Request(url, headers={"User-Agent": "PhoxTools/2.0"})
            with _ur.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            words = [w.strip().lower() for w in content.splitlines()
                     if w.strip() and not w.startswith("#") and w.strip().isascii()]
            if words:
                cache_file.write_text(chr(10).join(words), encoding="utf-8")
                return words
        except Exception:
            continue
    return None



def generate_brute(max_length=4, charset=None):
    if charset is None:
        charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
    total = sum(len(charset) ** i for i in range(1, max_length + 1))
    info(f"Brute-force: generating {total} combinations (charset={len(charset)}, max_len={max_length})")
    for length in range(1, max_length + 1):
        for combo in itertools.product(charset, repeat=length):
            yield ''.join(combo)

def register(subs):
    p = subs.add_parser("subdomain", help="Enumerate subdomains of a domain")
    p.add_argument("domain", help="Target domain")
    p.add_argument("-w", "--wordlist", default=None,
                   help="Custom wordlist file (one subdomain per line)")
    p.add_argument("-t", "--timeout", type=float, default=3.0,
                   help="DNS/HTTP timeout (default: 3.0)")
    p.add_argument("-c", "--concurrency", type=int, default=20,
                   help="Concurrent threads (default: 20)")
    p.add_argument("--dns-only", action="store_true",
                   help="Only check DNS (skip HTTP probe)")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.add_argument("-o", "--output", default=None,
                   help="Save results to file")
    p.add_argument("-l", "--large", action="store_true",
                   help="Download and use large wordlist (~5000-20000 subdomains)")
    p.add_argument("-b", "--brute", action="store_true",
                   help="Brute-force: generate ALL character combinations (a-z, 0-9)")
    p.add_argument("--max-length", type=int, default=4,
                   help="Max combination length for brute-force (default: 4)")
    p.set_defaults(func=cmd)


def load_wordlist(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        error(f"Wordlist not found: {path}")
        return None


def check_subdomain(domain, subdomain, timeout):
    fqdn = f"{subdomain}.{domain}"

    try:
        ip = socket.gethostbyname(fqdn)
    except socket.gaierror:
        return None

    return {
        "subdomain": fqdn,
        "ip": ip,
    }


def check_wildcard(domain):
    import random
    import string
    random_label = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    fqdn = f"{random_label}.{domain}"
    try:
        ip = socket.gethostbyname(fqdn)
        return True, ip
    except socket.gaierror:
        return False, None


def cmd(args):
    domain = args.domain.lower().strip()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.rstrip("/")

    if args.wordlist:
        words = load_wordlist(args.wordlist)
        if words is None:
            return
    elif args.brute:
        words = list(generate_brute(max_length=args.max_length))
    elif args.large:
        info("Downloading large wordlist from SecLists...")
        large = download_large_wordlist()
        if large:
            words = large
            info(f"Using large wordlist ({len(words)} entries)")
        else:
            warning("Failed to download large wordlist, using built-in")
            words = COMMON_SUBDOMAINS
    else:
        words = COMMON_SUBDOMAINS

    has_wildcard, wildcard_ip = check_wildcard(domain)
    if has_wildcard:
        warning(f"Wildcard DNS detected: *.{domain} resolves to {wildcard_ip}")
        warning("All results may include wildcard matches")

    info(f"Checking {len(words)} subdomains for {domain}")
    info(f"Timeout: {args.timeout}s, Threads: {args.concurrency}")

    results = []
    checked = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(check_subdomain, domain, word, args.timeout): word
            for word in words
        }

        for future in concurrent.futures.as_completed(futures):
            checked += 1
            if checked % 20 == 0 or checked == len(words):
                print(f"\r  Checked: {checked}/{len(words)}", end="", flush=True)

            result = future.result()
            if result is not None:
                results.append(result)
                ip_str = result["ip"] or "?"
                status_str = f"HTTP {result['status']}" if result["status"] else "DNS only"
                success(f"{result['subdomain']:<30} {ip_str:<16} {status_str}")

    print()
    print()

    if not results:
        warning("No subdomains found")
        return

    results.sort(key=lambda x: x["subdomain"])
    success(f"Found {len(results)} subdomains")

    if args.as_json:
        output = json.dumps(results, indent=2)
        print(output)
    else:
        print()
        print(f"  {'SUBDOMAIN':<40} {'IP':<20}")
        print(f"  {'-' * 40} {'-' * 20}")
        for r in results:
            ip = r["ip"] or "-"
            print(f"  {r['subdomain']:<40} {ip:<20}")
        print()
        if has_wildcard:
            warning("Note: Wildcard DNS detected - some results may be false positives")
        print()

    if args.output:
        out_path = OUTPUT_DIR / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(r['subdomain'] + "\n")
        success(f"Saved to {out_path}")
