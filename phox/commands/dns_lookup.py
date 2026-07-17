import json
import socket

from phox.config import success, error, info

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR"]


def dns_query(domain, record_type="A"):
    results = []
    if record_type in ("A", "AAAA"):
        try:
            fam = socket.AF_INET if record_type == "A" else socket.AF_INET6
            for info_tuple in socket.getaddrinfo(domain, None, fam):
                results.append(info_tuple[4][0])
        except socket.gaierror as e:
            error(f"Resolution failed: {e}")

    if record_type not in ("A", "AAAA") or not results:
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, record_type)
            for rdata in answers:
                results.append(str(rdata))
        except ImportError:
            if record_type not in ("A", "AAAA"):
                error("Install dnspython for advanced records: pip install dnspython")
        except Exception as e:
            error(f"DNS query failed: {e}")

    return results


def register(subs):
    p = subs.add_parser("dns", help="DNS lookup")
    p.add_argument("domain")
    p.add_argument("-t", "--type", dest="record_type", default="A",
                   choices=RECORD_TYPES, help="Record type (default: A)")
    p.add_argument("--all-types", action="store_true",
                   help="Query all record types")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.set_defaults(func=cmd)


def cmd(args):
    record_types = RECORD_TYPES if args.all_types else [args.record_type.upper()]
    all_results = {}
    for rt in record_types:
        info(f"Querying {rt} records for {args.domain}...")
        all_results[rt] = dns_query(args.domain, rt)

    if args.as_json:
        print(json.dumps(all_results, indent=2))
        return

    for rt, results in all_results.items():
        print()
        print(f"  {rt} records for {args.domain}:")
        for r in results:
            print(f"    {r}")
        if not results:
            print("    No records found")
    print()
