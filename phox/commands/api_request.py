import json as json_mod
from phox.config import success, error, info, OUTPUT_DIR
from phox.lib.http import request as http_request


def parse_headers(header_list):
    headers = {}
    for h in header_list:
        if ":" in h:
            key, value = h.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers


def register(subs):
    p = subs.add_parser("api", help="Make HTTP API requests")
    p.add_argument("url")
    p.add_argument("-X", "--method", default="GET",
                   choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    p.add_argument("-H", "--header", dest="headers", nargs="+", default=[],
                   help="Headers (Key: Value)")
    p.add_argument("-d", "--data", dest="body", default=None,
                   help="Request body (JSON or string)")
    p.add_argument("--json-file", default=None,
                   help="Body from JSON file")
    p.add_argument("-o", "--output", default=None,
                   help="Save response to file")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--no-verify", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd)


def cmd(args):
    headers = parse_headers(args.headers)
    body = None

    if args.json_file:
        with open(args.json_file) as f:
            body = json_mod.load(f)
    elif args.body:
        try:
            body = json_mod.loads(args.body)
        except json_mod.JSONDecodeError:
            body = args.body

    info(f"{args.method} {args.url}")

    try:
        resp = http_request(
            args.method, args.url,
            headers=headers,
            data=body if isinstance(body, str) else None,
            json_body=body if isinstance(body, (dict, list)) else None,
            timeout=args.timeout,
            verify=not args.no_verify,
        )
    except Exception as e:
        error(f"Request failed: {e}")
        return

    print()
    sc = resp.status_code
    color = "success" if sc < 400 else "error"
    from phox.config import c
    print(f"  Status: {c(str(sc), color)} {resp.reason}")

    if args.verbose:
        print("  Headers:")
        for k, v in resp.headers.items():
            print(f"    {k}: {v}")
        print()

    ct = resp.headers.get("content-type", "")
    print(f"  Content-Type: {ct}")
    print(f"  Size: {len(resp.content)} bytes")
    print()

    if "json" in ct:
        try:
            print(json_mod.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
    else:
        print(resp.text[:5000])
        if len(resp.text) > 5000:
            print(f"\n  ... ({len(resp.text) - 5000} more)")

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = OUTPUT_DIR / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(resp.content)
        success(f"Saved to {out_path}")
    print()
