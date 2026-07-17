import json
import os
import sys
import hashlib
import base64
import urllib.parse
import itertools
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

STATIC_DIR = (Path(__file__).parent / "static").resolve()

_WORDLIST_CACHE = Path.home() / ".phox" / "wordlists"
_WORDLIST_CACHE.mkdir(parents=True, exist_ok=True)

_WORDLIST_URLS = [
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt",
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-20000.txt",
    "https://raw.githubusercontent.com/rez0/subdomains/main/subdomains.txt",
    "https://raw.githubusercontent.com/appsecco/bug-bounty-wordlists/master/subdomains.txt",
]


def _download_wordlist():
    import urllib.request as _ur
    cache_file = _WORDLIST_CACHE / "subdomains.txt"

    if cache_file.exists():
        import time as _t
        age = _t.time() - cache_file.stat().st_mtime
        if age < 86400:
            try:
                words = cache_file.read_text(encoding="utf-8", errors="replace").splitlines()
                return [w.strip().lower() for w in words if w.strip() and not w.startswith("#") and w.strip().isascii()]
            except Exception:
                pass

    for url in _WORDLIST_URLS:
        try:
            req = _ur.Request(url, headers={"User-Agent": "PhoxTools/2.0"})
            with _ur.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            words = [w.strip().lower() for w in content.splitlines()
                     if w.strip() and not w.startswith("#") and w.strip().isascii()]
            if len(words) > 100:
                cache_file.write_text("\n".join(words), encoding="utf-8")
                return words
        except Exception:
            continue
    return None


class PhoxHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", ""):
            path = "/index.html"

        if path.startswith("/static/"):
            path = path[len("/static/"):]

        parts = [p for p in path.split("/") if p and p not in (".", "..")]
        clean = "/".join(parts)

        try:
            file_path = (STATIC_DIR / clean).resolve()
        except (ValueError, OSError):
            self.send_error(400, "Bad Request")
            return

        if not str(file_path).startswith(str(STATIC_DIR)):
            self.send_error(403, "Forbidden")
            return

        if file_path.exists() and file_path.is_file():
            self._serve_file(file_path)
        else:
            index = STATIC_DIR / "index.html"
            if index.exists():
                self._serve_file(index)
            else:
                self.send_error(404, "Not Found")

    def _serve_file(self, file_path):
        ext = file_path.suffix.lower()
        content_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ct = content_types.get(ext, "application/octet-stream")

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._handle_api()
        else:
            self.send_error(404, "Not Found")

    def _handle_api(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {"error": "Invalid JSON"})
            return

        route = self.path.split("?")[0]
        try:
            handler = API_ROUTES.get(route)
            if handler:
                response = handler(data)
                self._json_response(200, response)
            else:
                self._json_response(404, {"error": f"Unknown route: {route}"})
        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _json_response(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        msg = str(args) if args else ""
        if "/api/" in msg or "Error" in msg or "error" in msg.lower():
            super().log_message(format, *args)



def api_encode(data):
    text = data.get("text", "")
    fmt = data.get("format", "base64")
    if fmt == "base64":
        return {"result": base64.b64encode(text.encode()).decode()}
    elif fmt == "hex":
        return {"result": text.encode().hex()}
    elif fmt == "url":
        return {"result": urllib.parse.quote(text, safe="")}
    return {"error": f"Unknown format: {fmt}"}


def api_decode(data):
    text = data.get("text", "")
    fmt = data.get("format", "base64")
    if fmt == "base64":
        return {"result": base64.b64decode(text.encode()).decode()}
    elif fmt == "hex":
        return {"result": bytes.fromhex(text).decode()}
    elif fmt == "url":
        return {"result": urllib.parse.unquote(text)}
    return {"error": f"Unknown format: {fmt}"}


def api_hash(data):
    text = data.get("text", "")
    algo = data.get("algo", "sha256")
    results = {}
    for a in ["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"]:
        h = hashlib.new(a)
        h.update(text.encode())
        results[a] = h.hexdigest()
    if algo == "all":
        return {"results": results}
    h = hashlib.new(algo)
    h.update(text.encode())
    return {"result": h.hexdigest(), "algo": algo}


def api_password(data):
    import secrets, string, random
    length = min(max(data.get("length", 16), 4), 128)
    count = min(max(data.get("count", 1), 1), 20)
    use_special = data.get("special", True)
    use_digits = data.get("digits", True)
    use_upper = data.get("upper", True)

    chars = string.ascii_lowercase
    if use_upper:
        chars += string.ascii_uppercase
    if use_digits:
        chars += string.digits
    if use_special:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    passwords = []
    for _ in range(count):
        pw = list(secrets.choice(chars) for _ in range(length))
        if use_upper:
            pw[0] = secrets.choice(string.ascii_uppercase)
        if use_digits:
            pw[1] = secrets.choice(string.digits)
        if use_special:
            pw[2] = secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?")
        random.SystemRandom().shuffle(pw)
        passwords.append("".join(pw))
    return {"passwords": passwords}


def api_ip_lookup(data):
    from phox.lib.http import get as http_get
    ip = data.get("ip", "")

    try:
        resp = http_get(f"https://ipwho.is/{ip}", timeout=10,
                        headers={"Accept": "application/json"})
        raw = resp.json()
        if raw.get("success"):
            conn = raw.get("connection", {})
            sec = raw.get("security", {})
            tz = raw.get("timezone", {})
            flag = raw.get("flag", {})
            result = {
                "ip":              raw.get("ip", "N/A"),
                "type":            raw.get("type", "N/A"),
                "continent":       raw.get("continent", "N/A"),
                "continent_code":  raw.get("continent_code", "N/A"),
                "country":         raw.get("country", "N/A"),
                "country_code":    raw.get("country_code", "N/A"),
                "is_eu":           raw.get("is_eu", False),
                "region":          raw.get("region", "N/A"),
                "region_code":     raw.get("region_code", "N/A"),
                "city":            raw.get("city", "N/A"),
                "latitude":        raw.get("latitude", "N/A"),
                "longitude":       raw.get("longitude", "N/A"),
                "zip":             raw.get("postal", "N/A"),
                "calling_code":    raw.get("calling_code", "N/A"),
                "capital":         raw.get("capital", "N/A"),
                "borders":         raw.get("borders", "N/A"),
                "flag_emoji":      flag.get("emoji", "N/A"),
                "flag_img":        flag.get("img", "N/A"),
                "timezone_id":     tz.get("id", "N/A"),
                "timezone_abbr":   tz.get("abbr", "N/A"),
                "timezone_is_dst": tz.get("is_dst", False),
                "timezone_offset": tz.get("offset", "N/A"),
                "timezone_utc":    tz.get("utc", "N/A"),
                "asn":             conn.get("asn", "N/A"),
                "org":             conn.get("org", "N/A"),
                "isp":             conn.get("isp", "N/A"),
                "domain":          conn.get("domain", "N/A"),
                "reverse":         conn.get("reverse", "N/A"),
                "proxy":           sec.get("proxy", False),
                "vpn":             sec.get("vpn", False),
                "tor":             sec.get("tor", False),
                "relay":           sec.get("relay", False),
                "cloud":           sec.get("cloud", False),
                "mobile":          conn.get("type", "") == "cellular",
            }
            return {"result": result}
    except Exception:
        pass

    try:
        url = f"http://ip-api.com/json/{ip}?fields=66846719"
        resp = http_get(url, timeout=10)
        result = resp.json()
        if result.get("status") == "success":
            return {"result": {
                "ip": result.get("query", "N/A"),
                "type": "N/A",
                "continent": "N/A", "continent_code": "N/A",
                "country": result.get("country", "N/A"),
                "country_code": result.get("countryCode", "N/A"),
                "is_eu": False,
                "region": result.get("regionName", "N/A"),
                "region_code": result.get("region", "N/A"),
                "city": result.get("city", "N/A"),
                "latitude": result.get("lat", "N/A"),
                "longitude": result.get("lon", "N/A"),
                "zip": result.get("zip", "N/A"),
                "calling_code": "N/A", "capital": "N/A", "borders": "N/A",
                "flag_emoji": "N/A", "flag_img": "N/A",
                "timezone_id": result.get("timezone", "N/A"),
                "timezone_abbr": "N/A", "timezone_is_dst": False,
                "timezone_offset": "N/A", "timezone_utc": "N/A",
                "asn": result.get("as", "N/A"),
                "org": result.get("org", "N/A"),
                "isp": result.get("isp", "N/A"),
                "domain": "N/A", "reverse": result.get("reverse", "N/A"),
                "proxy": result.get("proxy", False),
                "vpn": False, "tor": False, "relay": False,
                "cloud": result.get("hosting", False),
                "mobile": result.get("mobile", False),
            }}
        return {"error": result.get("message", "Lookup failed")}
    except Exception as e:
        return {"error": str(e)}


def api_dns(data):
    import socket
    domain = data.get("domain", "")
    record_type = data.get("type", "A")
    results = []

    if record_type in ("A", "AAAA"):
        try:
            fam = socket.AF_INET if record_type == "A" else socket.AF_INET6
            for info in socket.getaddrinfo(domain, None, fam):
                results.append(info[4][0])
        except socket.gaierror as e:
            return {"error": str(e)}

    if record_type not in ("A", "AAAA") or not results:
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, record_type)
            for rdata in answers:
                results.append(str(rdata))
        except ImportError:
            return {"error": "Install dnspython for advanced record types"}
        except Exception as e:
            return {"error": str(e)}

    return {"results": results, "type": record_type, "domain": domain}


def api_whois(data):
    from phox.lib.http import get as http_get
    domain = data.get("domain", "").strip().lower()
    for p in ("https://", "http://"):
        if domain.startswith(p):
            domain = domain[len(p):]
    domain = domain.split("/")[0]

    try:
        resp = http_get(f"https://rdap.org/domain/{domain}",
                        timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return {"result": resp.json()}
        elif resp.status_code == 404:
            return {"error": f"Domain '{domain}' not found"}
        return {"error": f"RDAP failed (status {resp.status_code})"}
    except Exception as e:
        return {"error": str(e)}


def api_username(data):
    import concurrent.futures
    from phox.lib.http import get as http_get

    name = data.get("name", "")
    platforms = data.get("platforms", None)

    PLATFORMS = {
        "twitter":     {"url": "https://x.com/{}",                  "check": lambda r: r.status_code == 404},
        "instagram":   {"url": "https://www.instagram.com/{}/",      "check": lambda r: r.status_code == 404},
        "reddit":      {"url": "https://www.reddit.com/user/{}",     "check": lambda r: r.status_code == 404},
        "tiktok":      {"url": "https://www.tiktok.com/@{}",         "check": lambda r: r.status_code == 404},
        "youtube":     {"url": "https://www.youtube.com/@{}",        "check": lambda r: r.status_code == 404},
        "twitch":      {"url": "https://www.twitch.tv/{}",           "check": lambda r: r.status_code == 404},
        "pinterest":   {"url": "https://www.pinterest.com/{}/",      "check": lambda r: r.status_code == 404},
        "linkedin":    {"url": "https://www.linkedin.com/in/{}",     "check": lambda r: r.status_code == 404},
        "medium":      {"url": "https://medium.com/@{}",             "check": lambda r: r.status_code == 404},
        "snapchat":    {"url": "https://www.snapchat.com/add/{}",    "check": lambda r: r.status_code == 404},
        "facebook":    {"url": "https://www.facebook.com/{}",        "check": lambda r: r.status_code == 404},
        "threads":     {"url": "https://www.threads.net/@{}",        "check": lambda r: r.status_code == 404},
        "bluesky":     {"url": "https://bsky.app/profile/{}",        "check": lambda r: r.status_code == 404},
        "github":      {"url": "https://github.com/{}",              "check": lambda r: r.status_code == 404},
        "gitlab":      {"url": "https://gitlab.com/{}",              "check": lambda r: r.status_code == 404},
        "bitbucket":   {"url": "https://bitbucket.org/{}/",          "check": lambda r: r.status_code == 404},
        "deviantart":  {"url": "https://www.deviantart.com/{}",      "check": lambda r: r.status_code == 404},
        "npm":         {"url": "https://www.npmjs.com/~{}",          "check": lambda r: r.status_code == 404},
        "pypi":        {"url": "https://pypi.org/user/{}/",          "check": lambda r: r.status_code == 404},
        "codepen":     {"url": "https://codepen.io/{}",              "check": lambda r: r.status_code == 404},
        "replit":      {"url": "https://replit.com/@{}",             "check": lambda r: r.status_code == 404},
        "keybase":     {"url": "https://keybase.io/{}",              "check": lambda r: r.status_code == 404},
        "steam":       {"url": "https://steamcommunity.com/id/{}",   "check": lambda r: r.status_code == 404},
        "spotify":     {"url": "https://open.spotify.com/user/{}",   "check": lambda r: r.status_code == 404},
        "soundcloud":  {"url": "https://soundcloud.com/{}",          "check": lambda r: r.status_code == 404},
        "vimeo":       {"url": "https://vimeo.com/{}",               "check": lambda r: r.status_code == 404},
        "flickr":      {"url": "https://www.flickr.com/people/{}",   "check": lambda r: r.status_code == 404},
        "telegram":    {"url": "https://t.me/{}",                    "check": lambda r: r.status_code == 404},
        "pastebin":    {"url": "https://pastebin.com/u/{}",          "check": lambda r: r.status_code == 404},
        "hackerone":   {"url": "https://hackerone.com/{}",           "check": lambda r: r.status_code == 404},
        "gravatar":    {"url": "https://en.gravatar.com/{}",         "check": lambda r: r.status_code == 404},
        "roblox":      {"url": "https://www.roblox.com/user.aspx?username={}", "check": lambda r: r.status_code == 404},
        "epicgames":   {"url": "https://www.epicgames.com/site/en-US/u/{}", "check": lambda r: r.status_code == 404},
        "behance":     {"url": "https://www.behance.net/{}",         "check": lambda r: r.status_code == 404},
    }

    check = platforms or list(PLATFORMS.keys())
    results = []

    def check_one(pname):
        pc = PLATFORMS[pname]
        url = pc["url"].format(name)
        try:
            resp = http_get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            return {"platform": pname, "available": pc["check"](resp), "url": url}
        except Exception as e:
            return {"platform": pname, "available": None, "url": url, "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        futs = {ex.submit(check_one, p): p for p in check if p in PLATFORMS}
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())

    results.sort(key=lambda x: x["platform"])
    return {"results": results}


def api_qr(data):
    import urllib.parse
    import urllib.request as _ur
    text = data.get("text", "")
    fmt = data.get("format", "svg")
    size = min(max(data.get("size", 300), 100), 1000)

    if fmt == "text" or fmt == "txt":
        try:
            from phox.lib.qr import generate, to_text
            matrix = generate(text)
            return {"result": to_text(matrix), "format": "text"}
        except Exception as e:
            return {"error": str(e)}

    try:
        encoded = _up.quote(text, safe="")
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}&format=svg"
        req = _ur.Request(api_url, headers={"User-Agent": "Phox/1.0"})
        with _ur.urlopen(req, timeout=15) as resp:
            svg = resp.read().decode("utf-8")
            if "<svg" in svg:
                return {"result": svg, "format": "svg"}
    except Exception:
        pass

    try:
        from phox.lib.qr import generate, to_svg
        matrix = generate(text)
        return {"result": to_svg(matrix), "format": "svg"}
    except Exception as e:
        return {"error": str(e)}


def api_obfuscate(data):
    from phox.commands.obfuscator import obfuscate_code
    code = data.get("code", "")
    layers = min(max(data.get("layers", 1), 1), 5)
    try:
        result = obfuscate_code(code, layers=layers, junk=True)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def api_search(data):
    import re
    from phox.lib.http import post as http_post
    query = data.get("query", "")
    if not query:
        return {"error": "No query provided"}

    try:
        resp = http_post(
            "https://html.duckduckgo.com/html/",
            data="q=" + urllib.parse.quote(query),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}

    results = []
    blocks = re.split(r'<div class="result[^"]*">', resp.text)
    for block in blocks[1:15]:
        title_m = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_m = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
        if title_m:
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
            href_m = re.search(r'href="([^"]+)"', title_m.group(0))
            url = href_m.group(1) if href_m else ""
            snippet = re.sub(r"<[^>]+>", "", snippet_m.group(1)).strip() if snippet_m else ""
            results.append({"title": title, "url": url, "snippet": snippet})
    return {"results": results}


def api_api_request(data):
    from phox.lib.http import request as http_request
    url = data.get("url", "")
    method = data.get("method", "GET")
    headers = data.get("headers", {})
    body = data.get("body", None)

    json_body = None
    raw_data = None
    if body:
        if isinstance(body, (dict, list)):
            json_body = body
        else:
            raw_data = str(body)

    try:
        resp = http_request(method, url, headers=headers,
                            data=raw_data, json_body=json_body,
                            timeout=data.get("timeout", 30))
        result = {
            "status": resp.status_code,
            "reason": resp.reason,
            "headers": dict(resp.headers),
            "size": len(resp.content),
        }
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            try:
                result["body"] = resp.json()
            except Exception:
                result["body"] = resp.text[:5000]
        else:
            result["body"] = resp.text[:5000]
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}



def api_random(data):
    import secrets as _sec, string as _str, uuid as _uuid
    import random as _rnd
    rtype = data.get('type', 'string')
    count = min(max(data.get('count', 1), 1), 50)
    length = min(max(data.get('length', 16), 1), 1024)
    results = []
    for _ in range(count):
        if rtype == 'string':
            chars = _str.ascii_letters + _str.digits
            results.append(''.join(_sec.choice(chars) for _ in range(length)))
        elif rtype == 'hex':
            results.append(_sec.token_hex(length // 2 + 1)[:length])
        elif rtype == 'bytes':
            results.append(_sec.token_bytes(length).hex())
        elif rtype == 'uuid':
            results.append(str(_uuid.uuid4()))
        elif rtype == 'number':
            lo = data.get('min', 0)
            hi = data.get('max', 999999)
            results.append(str(_sec.randbelow(hi - lo + 1) + lo))
        elif rtype == 'password':
            chars = _str.ascii_letters + _str.digits + '!@#$%^&*()-_=+'
            pw = list(_sec.choice(chars) for _ in range(length))
            pw[0] = _sec.choice(_str.ascii_uppercase)
            pw[1] = _sec.choice(_str.digits)
            pw[2] = _sec.choice('!@#$%^&*')
            _rnd.SystemRandom().shuffle(pw)
            results.append(''.join(pw))
        elif rtype == 'dice':
            sides = data.get('sides', 6)
            results.append(str(_sec.randbelow(sides) + 1))
        elif rtype == 'coin':
            results.append(_sec.choice(['Heads', 'Tails']))
        elif rtype == 'choice':
            options = data.get('options', ['yes', 'no'])
            if isinstance(options, str):
                options = options.split(',')
            results.append(_sec.choice(options).strip())
        else:
            results.append('Unknown type')
    return {'results': results, 'type': rtype}


def api_portscan(data):
    import socket
    import concurrent.futures
    host = data.get('host', '').strip()
    if not host:
        return {'error': 'No host provided'}
    port_str = data.get('ports', 'top20')
    timeout = min(max(data.get('timeout', 1.0), 0.1), 5.0)
    max_threads = min(max(data.get('threads', 50), 1), 200)
    TOP_PORTS = [21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,
                 1433,1521,2049,3306,3389,5432,5900,6379,8080,8443,
                 8888,9090,27017]
    if port_str == 'top20':
        ports = TOP_PORTS[:20]
    elif port_str == 'top100':
        ports = TOP_PORTS
    elif ',' in str(port_str):
        ports = [int(p.strip()) for p in str(port_str).split(',') if p.strip().isdigit()]
    elif '-' in str(port_str):
        parts = str(port_str).split('-')
        start, end = int(parts[0]), int(parts[1])
        ports = list(range(start, min(end + 1, start + 10000)))
    else:
        try:
            ports = [int(port_str)]
        except ValueError:
            ports = TOP_PORTS

    open_ports = []
    def check_port(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((host, p))
            s.close()
            return p if result == 0 else None
        except Exception:
            return None

    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror as e:
        return {'error': f'Cannot resolve host: {e}'}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as ex:
        futures = {ex.submit(check_port, p): p for p in ports}
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r is not None:
                open_ports.append(r)
    open_ports.sort()
    return {'open': open_ports, 'host': host, 'ip': ip, 'scanned': len(ports)}


def api_subdomain(data):
    import socket
    import concurrent.futures
    import re as _re
    domain = data.get('domain', '').strip().lower()
    if not domain:
        return {'error': 'No domain provided'}
    for prefix in ('https://', 'http://'):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.split('/')[0].strip('.')
    if not domain or '.' not in domain:
        return {'error': f'Invalid domain: {domain}'}
    max_threads = min(max(data.get('threads', 30), 1), 200)
    use_large = data.get('large_wordlist', False)
    use_brute = data.get('brute', False)
    brute_max_len = min(max(data.get('max_length', 4), 1), 6)

    BUILTIN = [
        'www','mail','smtp','pop','pop3','imap','webmail','mx','mx1','mx2','mx3',
        'ns1','ns2','ns3','ns4','ns5','dns','dns1','dns2',
        'ftp','sftp','ssh','telnet','vpn','remote','gateway',
        'api','dev','development','staging','stage','test','testing','qa','uat',
        'sandbox','preprod','pre-production','preview','canary','nightly',
        'ci','cd','jenkins','travis','gitlab','github','drone','circle',
        'docker','k8s','kubernetes','swarm','rancher','registry',
        'git','gitlab','bitbucket','gogs','gitea','svn','stash',
        'sonar','nexus','artifactory','jfrog','harbor','mirror',
        'grafana','prometheus','kibana','elastic','elasticsearch','logstash',
        'datadog','sentry','newrelic','statuspage','uptime','health',
        'admin','administrator','panel','cpanel','whm','webmin','plesk',
        'cp','login','signin','auth','oauth','sso','id','identity',
        'portal','dashboard','manage','management','console','root',
        'db','database','mysql','mariadb','postgres','postgresql','psql',
        'redis','redis6','redis7','mongo','mongodb','mongo0','elastic',
        'memcache','memcached','cassandra','couchdb','influxdb','timescale',
        'neo4j','couchbase','riak','dynamodb','sqlite',
        'mq','rabbitmq','kafka','kafka0','kafka1','kafka2','activemq',
        'nats','amqp','zeromq','celery','worker','queue',
        'cdn','static','assets','media','img','images','image','images2',
        'video','videos','upload','uploads','files','file','download',
        'downloads','content','ressources','resources','public','private',
        'storage','s3','bucket','blob','store','shop','store2',
        'aws','s3','ec2','lambda','azure','gcp','google','cloud',
        'cloudflare','akamai','fastly','cloudfront','edge','origin',
        'heroku','vercel','netlify','firebase','appspot','railway',
        'render','fly','digitalocean','linode','vultr','hcloud',
        'app','web','site','www2','www3','www4','www5','www6',
        'beta','alpha','demo','preview','live','production','prod',
        'old','new','archive','legacy','classic','next','v2','v3','v4','v5',
        'blog','news','forum','community','wiki','help','support','docs',
        'doc','documentation','kb','faq','learn','academy','courses',
        'shop','store','commerce','checkout','pay','payment','payments',
        'cart','billing','invoice','merchant','affiliate','partners',
        'order','orders','catalog','product','products','marketplace',
        'mail2','email','newsletter','campaign','marketing','promo',
        'analytics','stats','statistics','metrics','insights','tracking',
        'pixel','tag','ads','ad','ads2','adserver','banner','survey',
        'chat','messaging','msg','message','messages','talk','call',
        'voip','sip','phone','fax','sms','push','notify','notification',
        'slack','teams','discord','mattermost','rocket','element',
        'secure','security','ssl','tls','cert','certs','certificate',
        'owa','exchange','exchange2','autodiscover','autoconfig',
        'firewall','ids','ips','waf','scan','pentest','vulnerability',
        'bug','bugs','bounty','hackerone','securitytxt','.well-known',
        'intranet','internal','private','corp','corporate','office',
        'hr','crm','erp','sap','salesforce','jira','confluence',
        'bamboo','trello','asana','notion','monday','clickup',
        'vpn2','rdp','bastion','jump','tunnel','proxy','squid',
        'api2','api3','api-v1','api-v2','api-v3','rest','graphql','ws',
        'socket','socket.io','ws2','wss','sse','grpc',
        '0','1','2','3','4','5','6','7','8','9','10',
        '01','02','03','04','05','06','07','08','09','100','200','300',
        'us','uk','eu','de','fr','es','it','nl','be','ch','at',
        'au','ca','jp','cn','in','br','ru','sg','hk','se','no','dk',
        'ny','sf','la','nyc','lon','par','tyo','syd','mel','tor',
        'm','mobile','touch','wap','lite','amp','pwa','sw',
        'app2','go','link','links','redirect','redir','r',
        'i','img','img2','pic','pics','photo','photos','thumb','thumbs',
        'asset','assets2','res','static2','pub','dist','build','bundle',
        'node','node1','node2','node3','server','server1','server2',
        'host','host1','host2','cluster','lb','loadbalancer','haproxy',
        'nginx','apache','caddy','traefik','istio','envoy',
        'backup','backups','bak','old','tmp','temp','cache','proxy2',
        'log','logs','error','errors','debug','trace','audit',
        'monitor','monitoring','apm','observability','trace2','span',
        'status','uptime','ping','heartbeat','alive','ready',
        'data','dataset','datasets','warehouse','lake','pipelines',
        'etl','airflow','prefect','dagster','luigi','spark',
        'hadoop','hive','presto','trino','superset','tableau','metabase',
        'grafana2','kibana2','alertmanager','thanos','cortex','loki',
    ]

    WORDLIST = BUILTIN
    wordlist_source = 'builtin'
    if use_brute:
        charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
        WORDLIST = [''.join(c) for i in range(1, brute_max_len + 1) for c in itertools.product(charset, repeat=i)]
        wordlist_source = f'brute-force ({len(WORDLIST)} combos, max_len={brute_max_len})'
    elif use_large:
        downloaded = _download_wordlist()
        if downloaded:
            WORDLIST = downloaded
            wordlist_source = f'downloaded ({len(downloaded)} words)'

    def check_sub(sub, timeout=3):
        result = [None]
        def _resolve():
            try:
                result[0] = socket.gethostbyname(f'{sub}.{domain}')
            except Exception:
                pass
        t = threading.Thread(target=_resolve, daemon=True)
        t.start()
        t.join(timeout)
        if result[0]:
            return f'{sub}.{domain}'
        return None

    # Wildcard detection
    import random as _rnd, string as _str
    rnd_label = ''.join(_rnd.choices(_str.ascii_lowercase + _str.digits, k=16))
    has_wildcard = False
    wildcard_ip = None
    try:
        result_w = [None]
        def _wc():
            try: result_w[0] = socket.gethostbyname(f'{rnd_label}.{domain}')
            except Exception: pass
        wt = threading.Thread(target=_wc, daemon=True)
        wt.start()
        wt.join(3)
        if result_w[0]:
            has_wildcard = True
            wildcard_ip = result_w[0]
    except Exception:
        pass

    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as ex:
        futures = {ex.submit(check_sub, s): s for s in WORDLIST}
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                found.append(r)
    found.sort()
    return {
        'subdomains': found,
        'domain': domain,
        'total': len(found),
        'wildcard': has_wildcard,
        'wildcard_ip': wildcard_ip,
        'wordlist_source': wordlist_source,
        'wordlist_size': len(WORDLIST),
    }


def api_save_ip(data):
    from datetime import datetime
    result = data.get("result", None)
    if not result:
        return {"error": "No result data to save"}
    save_dir = Path.home() / ".phox" / "output" / "ip-lookup"
    save_dir.mkdir(parents=True, exist_ok=True)
    ip_label = str(result.get("ip", "unknown")).replace(":", "_").replace(".", "_")
    path = save_dir / f"{ip_label}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return {"saved": str(path)}


def api_save_username(data):
    from datetime import datetime
    results = data.get("results", [])
    username = data.get("username", "unknown")
    if not results:
        return {"error": "No results to save"}
    avail = [r["platform"] for r in results if r.get("available")]
    taken = [r["platform"] for r in results if not r.get("available") and not r.get("error")]
    save_data = {
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "available": len(avail),
            "taken": len(taken),
            "errors": len(results) - len(avail) - len(taken),
            "total": len(results),
        },
        "available_on": avail,
        "taken_on": taken,
        "results": results,
    }
    save_dir = Path.home() / ".phox" / "output" / "username"
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{username}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    return {"saved": str(path)}


def api_hash_file(data):
    import hashlib
    content_b64 = data.get("content", "")
    algo = data.get("algo", "sha256")
    filename = data.get("filename", "file")
    if not content_b64:
        return {"error": "No file content provided"}
    try:
        import base64 as _b64
        raw = _b64.b64decode(content_b64)
    except Exception:
        return {"error": "Invalid base64 content"}
    results = {}
    for a in ["md5", "sha1", "sha256", "sha512"]:
        h = hashlib.new(a)
        h.update(raw)
        results[a] = h.hexdigest()
    if algo == "all":
        return {"results": results, "filename": filename, "size": len(raw)}
    h = hashlib.new(algo)
    h.update(raw)
    return {"result": h.hexdigest(), "algo": algo, "filename": filename, "size": len(raw)}


def api_cloner_start(data):
    from phox.config import CLONED_DIR
    from phox.lib.http import get as http_get
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from urllib.parse import urlparse, urljoin, urldefrag

    url = data.get("url", "").strip()
    depth = min(max(data.get("depth", 2), 1), 5)
    concurrency = min(max(data.get("concurrency", 5), 1), 20)
    include_external = data.get("include_external", True)
    if not url:
        return {"error": "No URL provided"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base_domain = parsed.netloc
    save_dir = CLONED_DIR / base_domain.replace(".", "_")
    save_dir.mkdir(parents=True, exist_ok=True)
    cloned_files = []
    visited = set()
    external_dir = save_dir / "_external"

    def is_asset_url(u):
        path = urlparse(u).path.lower()
        for ext in ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                     '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf',
                     '.map', '.webp', '.avif', '.mp4', '.webm', '.mp3',
                     '.json', '.xml', '.txt', '.pdf'):
            if path.endswith(ext):
                return True
        for seg in ('/js/', '/css/', '/font', '/images/', '/img/', '/assets/',
                     '/static/', '/media/', '/dist/', '/build/', '/lib/', '/vendor/'):
            if seg in path:
                return True
        return False

    def url_to_file(page_url):
        p = urlparse(page_url)
        url_domain = p.netloc
        is_external = url_domain != base_domain
        path = p.path.strip("/")
        if not path:
            path = "index.html"

        basename = path.rsplit("/", 1)[-1] if "/" in path else path
        ext = ""
        if "." in basename:
            ext = "." + basename.rsplit(".", 1)[-1].lower()

        if is_external:
            base = external_dir / url_domain.replace(".", "_")
        else:
            base = save_dir

        asset_exts = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                       '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf',
                       '.map', '.webp', '.avif', '.mp4', '.webm', '.mp3',
                       '.json', '.xml', '.txt', '.pdf')
        if ext in asset_exts:
            return base / path
        if ext in ('.html', '.htm', '.php', '.asp', '.aspx', '.jsp'):
            path = path[:-len(ext)]
        return base / (path + ".html")

    def fetch_one(u):
        try:
            r = http_get(u, timeout=15, headers={"User-Agent": "PhoxCloner/2.0"})
            return u, r.status_code, r.headers.get("content-type", ""), r.content
        except Exception:
            return u, None, "", b""

    def is_same_domain(full_url):
        return urlparse(full_url).netloc == base_domain

    def _detect_content_type(body, url_path, ct_header):
        ct = ct_header.lower().split(";")[0].strip() if ct_header else ""
        if ct and ct != "application/octet-stream":
            return ct
        try:
            head = body[:512].decode("utf-8", errors="replace").lstrip().lower()
        except Exception:
            return ct or "application/octet-stream"
        if head.startswith("<!doctype") or head.startswith("<html"):
            return "text/html"
        if head.startswith("<?xml") or ("<html" in head[:200]):
            return "text/html"
        ext = ""
        basename = url_path.rsplit("/", 1)[-1] if "/" in url_path else url_path
        if "." in basename:
            ext = "." + basename.rsplit(".", 1)[-1].lower()
        ext_map = {
            ".css": "text/css", ".js": "application/javascript",
            ".json": "application/json", ".xml": "text/xml",
            ".svg": "image/svg+xml", ".png": "image/png",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp",
            ".ico": "image/x-icon", ".woff": "font/woff",
            ".woff2": "font/woff2", ".ttf": "font/ttf",
            ".txt": "text/plain",
        }
        if ext in ext_map:
            return ext_map[ext]
        if head[:5] in ('<?xml', '{\"', '[\"', '/**', '/*!', '(function'):
            return ct or "application/octet-stream"
        return ct or "text/html"

    def extract_links_from_html(html, base_url):
        pages = []
        assets = []
        seen = set()

        def _add(url_val, target):
            if url_val in seen or url_val.startswith("data:"):
                return
            seen.add(url_val)
            target.append(url_val)

        for m in re.finditer(r'href=["\']([^"\'\s#]+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if is_same_domain(full) and full not in visited:
                _add(full, pages)
        for m in re.finditer(r'<link\s[^>]*href=["\']([^"\']+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if full not in visited:
                _add(full, assets)
        for m in re.finditer(r'<script\s[^>]*src=["\']([^"\']+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if full not in visited:
                _add(full, assets)
        for m in re.finditer(r'<img\s[^>]*src=["\']([^"\']+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if full not in visited:
                _add(full, assets)
        for m in re.finditer(r'srcset=["\']([^"\']+)["\']', html, re.I):
            for part in m.group(1).split(','):
                src = part.strip().split()[0]
                if src:
                    full = urljoin(base_url, urldefrag(src)[0])
                    if full not in visited:
                        _add(full, assets)
        for m in re.finditer(r'<meta\s[^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if full not in visited:
                _add(full, assets)
        for m in re.finditer(r'url\(["\']?([^"\')\s]+)["\']?\)', html, re.I):
            ref = m.group(1)
            if ref.startswith("data:"):
                continue
            full = urljoin(base_url, urldefrag(ref)[0])
            if full not in visited:
                _add(full, assets)
        for m in re.finditer(r'<(?:video|audio)\s[^>]*src=["\']([^"\']+)["\']', html, re.I):
            full = urljoin(base_url, urldefrag(m.group(1))[0])
            if full not in visited:
                _add(full, assets)
        return pages, assets

    def extract_links_from_css(css_text, css_url):
        assets = []
        seen = set()
        for m in re.finditer(r'@import\s+(?:url\(["\']?([^"\')\s]+)["\']?\)|["\']([^"\']+)["\'])', css_text, re.I):
            ref = m.group(1) or m.group(2)
            full = urljoin(css_url, urldefrag(ref)[0])
            if full not in seen and not full.startswith("data:"):
                seen.add(full)
                assets.append(full)
        for m in re.finditer(r'url\(["\']?([^"\')\s]+)["\']?\)', css_text, re.I):
            ref = m.group(1)
            if ref.startswith("data:"):
                continue
            full = urljoin(css_url, urldefrag(ref)[0])
            if full not in seen:
                seen.add(full)
                assets.append(full)
        return assets

    def extract_links_from_js(js_text, js_url):
        assets = []
        seen = set()
        for pat in [
            r'from\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\s*\(\s*["\']([^"\']+)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
        ]:
            for m in re.finditer(pat, js_text):
                ref = m.group(1)
                if ref.startswith((".", "/", "http")):
                    full = urljoin(js_url, urldefrag(ref)[0])
                    if full not in seen and full not in visited:
                        seen.add(full)
                        assets.append(full)
        return assets

    def download_and_parse(u):
        u, status, ct_header, body = fetch_one(u)
        if status != 200 or not body:
            return [], []
        visited.add(u)
        fp = url_to_file(u)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(body)
        cloned_files.append({"url": u, "file": str(fp), "size": len(body)})
        parsed_u = urlparse(u)
        ct = _detect_content_type(body, parsed_u.path, ct_header)
        new_pages = []
        new_assets = []
        try:
            text = body.decode("utf-8", errors="replace")
        except Exception:
            return [], []
        if "text/html" in ct:
            new_pages, new_assets = extract_links_from_html(text, u)
        elif "text/css" in ct:
            new_assets = extract_links_from_css(text, u)
        elif any(t in ct for t in ("javascript", ".js")):
            new_assets = extract_links_from_js(text, u)
        return new_pages, new_assets

    queue = [(url, 0)]
    all_assets = []

    while queue:
        batch = [(u, d) for u, d in queue if u not in visited and d <= depth]
        queue = []
        if not batch:
            break

        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {ex.submit(download_and_parse, u): (u, d) for u, d in batch}
            for f in as_completed(futures):
                new_pages, new_assets = f.result()
                for np_url in new_pages:
                    if np_url not in visited:
                        queue.append((np_url, futures[f][1] + 1))
                all_assets.extend(new_assets)

    asset_batch = [a for a in all_assets if a not in visited]
    seen_assets = set()
    unique_assets = []
    for a in asset_batch:
        if a not in seen_assets:
            seen_assets.add(a)
            unique_assets.append(a)

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures_map = {ex.submit(download_and_parse, a): a for a in unique_assets}
        for f in as_completed(futures_map):
            _, new_assets = f.result()
            if new_assets:
                extra = [a for a in new_assets if a not in visited and a not in seen_assets]
                for ea in extra:
                    seen_assets.add(ea)
                    try:
                        download_and_parse(ea)
                    except Exception:
                        pass

    return {
        "url": url,
        "domain": base_domain,
        "files": cloned_files,
        "total": len(cloned_files),
        "save_dir": str(save_dir),
    }


def api_webhook_send(data):
    from phox.lib.http import request as http_request
    url = data.get("url", "")
    method = data.get("method", "POST")
    payload = data.get("payload", "")
    headers = data.get("headers", {})
    headers.setdefault("Content-Type", "application/json")
    if not url:
        return {"error": "No URL provided"}
    import json as _json
    json_body = None
    try:
        json_body = _json.loads(payload) if payload else None
    except Exception:
        json_body = {"data": payload}
    try:
        resp = http_request(method, url, headers=headers, json_body=json_body, timeout=10)
        return {"status": resp.status_code, "body": resp.text[:2000]}
    except Exception as e:
        return {"error": str(e)}


def api_config_get(data):
    from phox.config import load_config, SETTINGS_META
    config = load_config()
    return {"config": config, "meta": SETTINGS_META}


def api_config_set(data):
    from phox.config import load_config, save_config
    key = data.get("key", "")
    value = data.get("value")
    if not key:
        return {"error": "No key provided"}
    config = load_config()
    parts = key.split(".")
    obj = config
    for part in parts[:-1]:
        if part not in obj:
            obj[part] = {}
        obj = obj[part]
    if isinstance(value, str):
        if value.lower() in ("true", "yes"):
            value = True
        elif value.lower() in ("false", "no"):
            value = False
        elif value.isdigit():
            value = int(value)
    obj[parts[-1]] = value
    save_config(config)
    return {"ok": True, "key": key, "value": value}



def api_uuid(data):
    import uuid as _uuid
    count = min(max(data.get("count", 1), 1), 50)
    version = data.get("version", "v4")
    results = []
    for _ in range(count):
        if version == "v1":
            results.append(str(_uuid.uuid1()))
        elif version == "v5":
            namespace = _uuid.uuid5(_uuid.NAMESPACE_DNS, data.get("namespace", "example.com"))
            results.append(str(_uuid.uuid5(namespace, data.get("name", "phox"))))
        else:
            results.append(str(_uuid.uuid4()))
    return {"results": results, "version": version}


def api_lorem(data):
    count = min(max(data.get("paragraphs", 3), 1), 50)
    words = [
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing",
        "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore",
        "et", "dolore", "magna", "aliqua", "enim", "ad", "minim", "veniam",
        "quis", "nostrud", "exercitation", "ullamco", "laboris", "nisi",
        "aliquip", "ex", "ea", "commodo", "consequat", "duis", "aute",
        "irure", "in", "reprehenderit", "voluptate", "velit", "esse",
        "cillum", "fugiat", "nulla", "pariatur", "excepteur", "sint",
        "occaecat", "cupidatat", "non", "proident", "sunt", "culpa",
        "qui", "officia", "deserunt", "mollit", "anim", "id", "est",
        "laborum", "vitae", "elementum", "curabitur", "sollicitudin",
        "purus", "viverra", "accumsan", "nisl", "nunc", "faucibus",
        "ornare", "suspendisse", "potenti", "nullam", "ac", "tortor",
        "dignissim", "convallis", "aenean", "pharetra", "lacus",
        "vel", "facilisis", "volutpat", "est", "quam", "sapien",
    ]
    import random
    rng = random.SystemRandom()
    paragraphs = []
    for _ in range(count):
        num_sentences = rng.randint(4, 8)
        sentences = []
        for _ in range(num_sentences):
            num_words = rng.randint(8, 18)
            sentence_words = [rng.choice(words) for _ in range(num_words)]
            sentence_words[0] = sentence_words[0].capitalize()
            sentences.append(" ".join(sentence_words) + ".")
        paragraphs.append(" ".join(sentences))
    return {"text": "\n\n".join(paragraphs), "paragraphs": count}


def api_diff(data):
    import difflib
    text1 = data.get("text1", "")
    text2 = data.get("text2", "")
    if not text1 and not text2:
        return {"error": "Provide two texts to compare"}
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)
    diff = list(difflib.unified_diff(lines1, lines2, fromfile="Text 1", tofile="Text 2", lineterm=""))
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    return {"diff": "\n".join(diff), "added": added, "removed": removed, "lines1": len(lines1), "lines2": len(lines2)}


def api_morse(data):
    text = data.get("text", "")
    mode = data.get("mode", "encode")
    MORSE = {
        "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
        "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
        "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
        "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
        "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
        "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
        "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..",
        "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...",
        ":": "---...", ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-",
        "_": "..--.-", '"': ".-..-.", "$": "...-..-", "@": ".--.-.", " ": "/",
    }
    MORSE_REV = {v: k for k, v in MORSE.items()}
    if mode == "encode":
        result = " ".join(MORSE.get(c.upper(), "?") for c in text)
    else:
        result = "".join(MORSE_REV.get(code, "?") for code in text.split(" "))
    return {"result": result, "mode": mode}


def api_binary(data):
    text = data.get("text", "")
    mode = data.get("mode", "to-binary")
    if mode == "to-binary":
        result = " ".join(format(ord(c), "08b") for c in text)
    else:
        chunks = text.strip().split()
        result = "".join(chr(int(c, 2)) for c in chunks if c)
    return {"result": result, "mode": mode}


def api_timestamp(data):
    from datetime import datetime, timezone
    action = data.get("action", "now")
    if action == "now":
        now = datetime.now(timezone.utc)
        return {
            "unix": int(now.timestamp()),
            "iso": now.isoformat(),
            "utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    elif action == "convert":
        value = data.get("value", "")
        try:
            ts = float(value)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return {
                "unix": int(ts),
                "iso": dt.isoformat(),
                "utc": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "local": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            return {"error": str(e)}
    elif action == "parse":
        value = data.get("value", "")
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
            try:
                dt = datetime.strptime(value, fmt)
                return {"unix": int(dt.timestamp()), "iso": dt.isoformat(), "utc": dt.strftime("%Y-%m-%d %H:%M:%S UTC")}
            except ValueError:
                continue
        return {"error": f"Cannot parse date: {value}"}
    return {"error": "Unknown action"}


def api_color_convert(data):
    value = data.get("value", "").strip()
    fmt = data.get("format", "hex")
    try:
        if fmt == "hex" or value.startswith("#"):
            hex_val = value.lstrip("#")
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        elif fmt == "rgb":
            parts = value.replace("rgb(", "").replace(")", "").split(",")
            r, g, b = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
        elif fmt == "hsl":
            parts = value.replace("hsl(", "").replace(")", "").split(",")
            h, s, l = float(parts[0].strip()), float(parts[1].strip().rstrip("%")), float(parts[2].strip().rstrip("%"))
            s, l = s / 100, l / 100
            c = (1 - abs(2 * l - 1)) * s
            x = c * (1 - abs((h / 60) % 2 - 1))
            m = l - c / 2
            if h < 60: r, g, b = c, x, 0
            elif h < 120: r, g, b = x, c, 0
            elif h < 180: r, g, b = 0, c, x
            elif h < 240: r, g, b = 0, x, c
            elif h < 300: r, g, b = x, 0, c
            else: r, g, b = c, 0, x
            r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
        elif fmt == "decimal":
            n = int(value)
            r, g, b = (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF
        else:
            return {"error": f"Unknown format: {fmt}"}
        hex_out = f"#{r:02x}{g:02x}{b:02x}"
        return {"hex": hex_out, "rgb": f"rgb({r}, {g}, {b})", "decimal": r * 65536 + g * 256 + b, "css": hex_out}
    except Exception as e:
        return {"error": str(e)}


def api_hash_lookup(data):
    import hashlib
    hash_val = data.get("hash", "").strip().lower()
    algo = data.get("algo", "auto")
    if not hash_val:
        return {"error": "No hash provided"}
    hlen = len(hash_val)
    if algo == "auto":
        if hlen == 32: algo = "md5"
        elif hlen == 40: algo = "sha1"
        elif hlen == 64: algo = "sha256"
        else: algo = "unknown"
    common = [
        "password", "123456", "12345678", "qwerty", "abc123", "monkey",
        "master", "dragon", "login", "princess", "football", "shadow",
        "sunshine", "trustno1", "iloveyou", "batman", "access",
        "hello", "charlie", "letmein", "welcome", "admin", "passw0rd",
        "test", "guest", "hello123", "password1", "123456789",
        "1234567890", "12345", "passpass", "test123", "root", "toor",
        "pass", "changeme", "secret", "default", "server", "master123",
        "abc123456", "a123456", "qwerty123", "1q2w3e4r", "zaq1xsw2",
        "000000", "111111", "a", "aa", "ab", "abc", "abcd",
    ]
    found = []
    for word in common:
        if algo == "md5": h = hashlib.md5(word.encode()).hexdigest()
        elif algo == "sha1": h = hashlib.sha1(word.encode()).hexdigest()
        elif algo == "sha256": h = hashlib.sha256(word.encode()).hexdigest()
        elif algo == "sha512": h = hashlib.sha512(word.encode()).hexdigest()
        else: continue
        if h == hash_val:
            found.append({"word": word, "algo": algo})
    return {"hash": hash_val, "algo": algo, "length": hlen, "found": found, "cracked": len(found) > 0}


def api_module_config(data):
    """Get/set module visibility configuration."""
    from phox.config import load_config, save_config
    config = load_config()
    if "web" not in config:
        config["web"] = {}
    if "modules" not in config["web"]:
        config["web"]["modules"] = {}
    action = data.get("action", "get")
    if action == "get":
        return {"modules": config["web"].get("modules", {})}
    elif action == "set":
        modules = data.get("modules", {})
        config["web"]["modules"].update(modules)
        save_config(config)
        return {"ok": True, "modules": config["web"]["modules"]}
    elif action == "reset":
        config["web"]["modules"] = {}
        save_config(config)
        return {"ok": True, "modules": {}}
    return {"error": "Unknown action"}


API_ROUTES = {
    "/api/encode":         api_encode,
    "/api/decode":         api_decode,
    "/api/hash":           api_hash,
    "/api/password":       api_password,
    "/api/ip-lookup":      api_ip_lookup,
    "/api/save-ip":        api_save_ip,
    "/api/dns":            api_dns,
    "/api/whois":          api_whois,
    "/api/username":       api_username,
    "/api/save-username":  api_save_username,
    "/api/qr":             api_qr,
    "/api/obfuscate":      api_obfuscate,
    "/api/search":         api_search,
    "/api/api-request":    api_api_request,
    "/api/random":         api_random,
    "/api/portscan":       api_portscan,
    "/api/subdomain":      api_subdomain,
    "/api/hash-file":      api_hash_file,
    "/api/cloner-start":   api_cloner_start,
    "/api/webhook-send":   api_webhook_send,
    "/api/config-get":     api_config_get,
    "/api/config-set":     api_config_set,
    "/api/uuid":           api_uuid,
    "/api/lorem":          api_lorem,
    "/api/diff":           api_diff,
    "/api/morse":          api_morse,
    "/api/binary":         api_binary,
    "/api/timestamp":      api_timestamp,
    "/api/color-convert":  api_color_convert,
    "/api/hash-lookup":    api_hash_lookup,
    "/api/module-config":  api_module_config,
}





def run_server(host="localhost", port=1234):
    """Start the Phox web UI server."""
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
    server = ThreadedHTTPServer((host, port), PhoxHandler)
    print(f"""
  \033[96m\033[1mPhox Web UI\033[0m
  \033[92m[+]\033[0m Running at: \033[1mhttp://localhost:{port}\033[0m
  \033[90m    Press Ctrl+C to stop\033[0m
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[91m[!] Server stopped\033[0m")
        server.shutdown()
