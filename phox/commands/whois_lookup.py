import json

from phox.config import success, error, info
from phox.lib.http import get as http_get


def whois_query(domain):
    domain = domain.strip().lower()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.split("/")[0]

    url = f"https://rdap.org/domain/{domain}"
    try:
        resp = http_get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            error(f"Domain '{domain}' not found")
        else:
            error(f"RDAP query failed with status {resp.status_code}")
    except Exception as e:
        error(f"Request failed: {e}")
    return None


def format_whois(data):
    if not data:
        return
    name = data.get("ldhName", "N/A")
    print(f"  {'Domain:':>20} {name}")

    statuses = data.get("status", [])
    if statuses:
        print(f"  {'Status:':>20} {', '.join(statuses)}")

    for event in data.get("events", []):
        et = event.get("eventAction", "")
        ed = event.get("eventDate", "")
        if et and ed:
            print(f"  {et.title() + ':':>20} {ed}")

    ns_list = data.get("nameservers", [])
    if ns_list:
        print(f"  {'Nameservers:':>20}")
        for ns in ns_list:
            print(f"    {ns.get('ldhName', 'N/A')}")

    for entity in data.get("entities", []):
        roles = entity.get("roles", [])
        handle = entity.get("handle", "")
        if roles:
            print(f"  {', '.join(roles).title() + ':':>20}")
        if handle:
            print(f"    Handle: {handle}")
        vcard = entity.get("vcardArray", [])
        if len(vcard) > 1:
            for item in vcard[1]:
                if item[0] == "fn":
                    print(f"    Name: {item[3]}")
                elif item[0] == "adr":
                    addr = " ".join(str(a) for a in item[3] if a)
                    print(f"    Address: {addr}")

    for link in data.get("links", []):
        if link.get("rel") == "self":
            print(f"  {'RDAP URL:':>20} {link.get('href', '')}")


def register(subs):
    p = subs.add_parser("whois", help="WHOIS/RDAP domain lookup")
    p.add_argument("domain")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.set_defaults(func=cmd)


def cmd(args):
    info(f"Looking up {args.domain}...")
    data = whois_query(args.domain)
    if not data:
        return
    if args.as_json:
        print(json.dumps(data, indent=2))
        return
    print()
    format_whois(data)
    print()
