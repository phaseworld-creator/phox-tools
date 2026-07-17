import concurrent.futures
import socket
import sys
import time

from phox.config import success, error, info, warning, c


WELL_KNOWN_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCBind", 135: "MSRPC",
    139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    27017: "MongoDB", 9200: "Elasticsearch",
}

TOP_20 = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
          443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443, 27017]

TOP_100 = [7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88, 106,
           110, 111, 113, 119, 135, 139, 143, 144, 179, 199, 389, 427,
           443, 444, 445, 465, 513, 514, 515, 543, 544, 548, 554, 587,
           631, 646, 873, 990, 993, 995, 1025, 1026, 1027, 1028, 1029,
           1110, 1433, 1720, 1723, 1755, 1900, 2000, 2001, 2049, 2103,
           2121, 2717, 3000, 3128, 3306, 3389, 3986, 4899, 5000, 5009,
           5051, 5101, 5190, 5357, 5432, 5631, 5666, 5800, 5900, 6000,
           6001, 6646, 7070, 8000, 8008, 8009, 8080, 8081, 8443, 8888,
           9100, 9999, 10000, 27017, 32768, 49152, 49153, 49154, 49155,
           49156, 49157, 50000, 50070]


def register(subs):
    p = subs.add_parser("portscan", help="Scan ports on a target")
    p.add_argument("host", help="Target host (IP or hostname)")
    p.add_argument("-p", "--ports", default=None,
                   help="Ports: '80,443' or '1-1000' or 'top100' (default: top20)")
    p.add_argument("-t", "--timeout", type=float, default=1.0,
                   help="Connection timeout in seconds (default: 1.0)")
    p.add_argument("-c", "--concurrency", type=int, default=50,
                   help="Max concurrent threads (default: 50)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Show closed ports too")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.set_defaults(func=cmd)


def parse_ports(port_str):
    if port_str is None:
        return TOP_20

    port_str = port_str.lower().strip()

    if port_str == "top20":
        return TOP_20
    if port_str == "top100":
        return TOP_100
    if port_str == "all":
        return list(range(1, 65536))

    ports = set()
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            ports.update(range(start, end + 1))
        else:
            ports.add(int(part))
    return sorted(ports)


def scan_port(host, port, timeout):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        service = WELL_KNOWN_PORTS.get(port, "")
        return port, result == 0, service
    except socket.gaierror:
        return port, None, "DNS_ERROR"
    except Exception:
        return port, None, "ERROR"


def cmd(args):
    host = args.host

    info(f"Resolving {host}...")
    try:
        ip = socket.gethostbyname(host)
        if ip != host:
            info(f"Resolved to {ip}")
    except socket.gaierror as e:
        error(f"Cannot resolve {host}: {e}")
        return

    ports = parse_ports(args.ports)
    port_count = len(ports)
    info(f"Scanning {port_count} port{'s' if port_count != 1 else ''} on {host} "
         f"(timeout={args.timeout}s, threads={args.concurrency})")

    start_time = time.time()
    open_ports = []
    closed_ports = []
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(scan_port, host, port, args.timeout): port
            for port in ports
        }
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            if done % 50 == 0 or done == port_count:
                print(f"\r  Progress: {done}/{port_count}", end="", flush=True)

            port, is_open, service = future.result()
            if is_open is None:
                errors += 1
            elif is_open:
                open_ports.append((port, service))
            else:
                closed_ports.append(port)

    elapsed = time.time() - start_time
    print()

    open_ports.sort(key=lambda x: x[0])

    print()
    if open_ports:
        success(f"Open ports found: {len(open_ports)}")
        print()
        print(f"  {'PORT':>8}  {'STATE':>8}  {'SERVICE'}")
        print(f"  {'─' * 8}  {'─' * 8}  {'─' * 20}")
        for port, service in open_ports:
            label = service or "unknown"
            print(f"  {port:>8}  {c('OPEN', 'success'):>17}  {label}")
    else:
        warning("No open ports found")

    print()
    print(f"  Scanned {port_count} ports in {elapsed:.1f}s")
    if args.verbose and closed_ports:
        print(f"  Closed: {len(closed_ports)}")
    if errors:
        print(f"  Errors: {errors}")
    print()
