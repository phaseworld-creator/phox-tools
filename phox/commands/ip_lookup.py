"""IP address geolocation lookup (pure stdlib)."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from phox.config import success, error, info, OUTPUT_DIR, c, t
from phox.lib.http import get as http_get


def lookup_ip(ip=None):
    """Lookup IP using ipwho.is (primary) with ip-api.com fallback."""
    target = ip or ""
    # Primary: ipwho.is (free, no key, full data)
    try:
        url = f"https://ipwho.is/{target}"
        resp = http_get(url, timeout=10, headers={"Accept": "application/json"})
        data = resp.json()
        if data.get("success"):
            return _normalize_ipwho(data)
    except Exception:
        pass

    # Fallback: ip-api.com
    try:
        url = f"http://ip-api.com/json/{target}?fields=66846719"
        resp = http_get(url, timeout=10)
        data = resp.json()
        if data.get("status") == "success":
            return _normalize_ipapi(data)
    except Exception:
        pass

    error("Both IP lookup APIs failed. Check your internet connection.")
    return None


def _normalize_ipwho(data):
    """Normalize ipwho.is response — extract every available field."""
    conn = data.get("connection", {})
    sec = data.get("security", {})
    tz = data.get("timezone", {})
    flag = data.get("flag", {})
    return {
        "ip":                data.get("ip", "N/A"),
        "type":              data.get("type", "N/A"),
        "continent":         data.get("continent", "N/A"),
        "continent_code":    data.get("continent_code", "N/A"),
        "country":           data.get("country", "N/A"),
        "country_code":      data.get("country_code", "N/A"),
        "is_eu":             data.get("is_eu", False),
        "region":            data.get("region", "N/A"),
        "region_code":       data.get("region_code", "N/A"),
        "city":              data.get("city", "N/A"),
        "latitude":          data.get("latitude", "N/A"),
        "longitude":         data.get("longitude", "N/A"),
        "zip":               data.get("postal", "N/A"),
        "calling_code":      data.get("calling_code", "N/A"),
        "capital":           data.get("capital", "N/A"),
        "borders":           data.get("borders", "N/A"),
        "flag_emoji":        flag.get("emoji", "N/A"),
        "flag_img":          flag.get("img", "N/A"),
        "timezone_id":       tz.get("id", "N/A"),
        "timezone_abbr":     tz.get("abbr", "N/A"),
        "timezone_is_dst":   tz.get("is_dst", False),
        "timezone_offset":   tz.get("offset", "N/A"),
        "timezone_utc":      tz.get("utc", "N/A"),
        "asn":               conn.get("asn", "N/A"),
        "org":               conn.get("org", "N/A"),
        "isp":               conn.get("isp", "N/A"),
        "domain":            conn.get("domain", "N/A"),
        "reverse":           conn.get("reverse", "N/A"),
        "proxy":             sec.get("proxy", False),
        "vpn":               sec.get("vpn", False),
        "tor":               sec.get("tor", False),
        "relay":             sec.get("relay", False),
        "cloud":             sec.get("cloud", False),
        "mobile":            conn.get("type", "") == "cellular",
    }


def _normalize_ipapi(data):
    """Normalize ip-api.com response to match ipwho.is field names."""
    return {
        "ip":                data.get("query", "N/A"),
        "type":              "N/A",
        "continent":         "N/A",
        "continent_code":    "N/A",
        "country":           data.get("country", "N/A"),
        "country_code":      data.get("countryCode", "N/A"),
        "is_eu":             False,
        "region":            data.get("regionName", "N/A"),
        "region_code":       data.get("region", "N/A"),
        "city":              data.get("city", "N/A"),
        "latitude":          data.get("lat", "N/A"),
        "longitude":         data.get("lon", "N/A"),
        "zip":               data.get("zip", "N/A"),
        "calling_code":      "N/A",
        "capital":           "N/A",
        "borders":           "N/A",
        "flag_emoji":        "N/A",
        "flag_img":          "N/A",
        "timezone_id":       data.get("timezone", "N/A"),
        "timezone_abbr":     "N/A",
        "timezone_is_dst":   False,
        "timezone_offset":   "N/A",
        "timezone_utc":      "N/A",
        "asn":               data.get("as", "N/A"),
        "org":               data.get("org", "N/A"),
        "isp":               data.get("isp", "N/A"),
        "domain":            "N/A",
        "reverse":           data.get("reverse", "N/A"),
        "proxy":             data.get("proxy", False),
        "vpn":               False,
        "tor":               False,
        "relay":             False,
        "cloud":             data.get("hosting", False),
        "mobile":            data.get("mobile", False),
    }


# ── Formatting helpers ───────────────────────────────────

def _bold(text):
    return c(text, "bold")


def _primary(text):
    return c(text, "primary")


def _muted(text):
    return c(text, "muted")


def _success_val(text):
    return c(text, "success")


def _error_val(text):
    return c(text, "error")


def _warning_val(text):
    return c(text, "warning")


def _info_val(text):
    return c(text, "info")


def format_ip_info(data):
    sections = [
        ("IP ADDRESS", [
            ("IP Address", "ip"),
            ("Type", "type"),
            ("Flag", "flag_emoji"),
        ]),
        ("LOCATION", [
            ("Continent", "continent"),
            ("Country", "country"),
            ("Country Code", "country_code"),
            ("EU Member", "is_eu"),
            ("Region", "region"),
            ("Region Code", "region_code"),
            ("City", "city"),
            ("Zip / Postal", "zip"),
            ("Capital", "capital"),
            ("Latitude", "latitude"),
            ("Longitude", "longitude"),
            ("Borders", "borders"),
        ]),
        ("TIMEZONE", [
            ("Timezone", "timezone_id"),
            ("Abbreviation", "timezone_abbr"),
            ("UTC Offset", "timezone_utc"),
            ("Offset (sec)", "timezone_offset"),
            ("DST Active", "timezone_is_dst"),
        ]),
        ("NETWORK", [
            ("ISP", "isp"),
            ("Organization", "org"),
            ("ASN", "asn"),
            ("Domain", "domain"),
            ("Calling Code", "calling_code"),
            ("Reverse DNS", "reverse"),
        ]),
    ]

    theme = t()

    print()
    print(f"  {_bold(theme['primary'] + '═══════════════════════════════════════════════════════' + theme['reset'])}")
    print(f"  {_bold(_primary('  IP LOOKUP RESULTS'))}")
    print(f"  {_bold(theme['primary'] + '═══════════════════════════════════════════════════════' + theme['reset'])}")
    print()

    for section_title, fields in sections:
        # Section header with colored divider
        print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")
        print(f"  {_bold(_primary(f'  {section_title}'))}")
        print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")

        for label, key in fields:
            val = data.get(key, "N/A")
            if val is True:
                display_val = _success_val("Yes")
            elif val is False:
                display_val = _error_val("No")
            elif val == "N/A" or val == "" or val is None:
                continue
            else:
                display_val = str(val)
            print(f"    {label:>18s}  {_muted('│')}  {display_val}")

        print()

    # ── Security flags section ──
    print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")
    print(f"  {_bold(_primary('  SECURITY'))}")
    print(f"  {theme['muted']}{'─' * 50}{theme['reset']}")

    sec_flags = []
    if data.get("proxy"):
        sec_flags.append(_warning_val("PROXY"))
    if data.get("vpn"):
        sec_flags.append(_warning_val("VPN"))
    if data.get("tor"):
        sec_flags.append(_error_val("TOR"))
    if data.get("relay"):
        sec_flags.append(_warning_val("RELAY"))
    if data.get("cloud"):
        sec_flags.append(_info_val("CLOUD"))
    if data.get("mobile"):
        sec_flags.append(_info_val("MOBILE"))

    print(f"    {'Flags':>18s}  {_muted('│')}  ", end="")
    if sec_flags:
        print(", ".join(sec_flags))
    else:
        print(_success_val("None detected"))

    print()
    print(f"  {_bold(theme['primary'] + '═══════════════════════════════════════════════════════' + theme['reset'])}")
    print()


def _save_result(data, output_path):
    """Save lookup result to file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    success(f"Saved to {out}")
    return str(out)


def register(subs):
    p = subs.add_parser("ip-lookup", help="IP address geolocation lookup")
    p.add_argument("ip", nargs="?", default=None,
                   help="IP to lookup (default: your IP)")
    p.add_argument("-o", "--output", default=None,
                   help="Save result to file")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.set_defaults(func=cmd)


def cmd(args):
    target = args.ip or "your public IP"
    info(f"Looking up {target}...")
    data = lookup_ip(args.ip)
    if not data:
        return

    # Auto-save to output dir (unless -o is set for custom path)
    save_dir = OUTPUT_DIR / "ip-lookup"
    save_dir.mkdir(parents=True, exist_ok=True)
    ip_label = (args.ip or "my_ip").replace(":", "_").replace(".", "_")
    auto_path = save_dir / f"{ip_label}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(auto_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    info(f"Auto-saved to {auto_path}")

    # Custom output path
    if args.output:
        _save_result(data, args.output)

    if args.as_json:
        print(json.dumps(data, indent=2))
        return
    format_ip_info(data)
