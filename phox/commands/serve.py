import sys
from pathlib import Path

from phox.config import banner, info, success, warning, load_config, c, t


def _count_pages():
    static_dir = Path(__file__).parent / "static"
    pages = list(static_dir.glob("*.html"))
    return len(pages)


def _show_starting(port, host="localhost"):
    theme = t()
    url = f"http://{host}:{port}"
    pages = _count_pages()

    print()
    print(f"  {theme['bold']}{theme['primary']}{'═' * 50}{theme['reset']}")
    print(f"  {theme['bold']}{theme['primary']}  PHOX Web UI{theme['reset']}")
    print(f"  {theme['bold']}{theme['primary']}{'═' * 50}{theme['reset']}")
    print()
    print(
        f"  {theme['success']}[+]{theme['reset']} "
        f"Server running at {theme['bold']}{theme['info']}{url}{theme['reset']}"
    )
    print(
        f"  {theme['success']}[+]{theme['reset']} "
        f"Pages available: {theme['bold']}{pages}{theme['reset']}"
    )
    print(
        f"  {theme['muted']}    Press Ctrl+C to stop{theme['reset']}"
    )
    print()
    print(f"  {theme['bold']}{theme['primary']}{'═' * 50}{theme['reset']}")
    print()


def _auto_open_browser(host, port):
    import webbrowser

    config = load_config()
    web_cfg = config.get("web", {})
    auto_open = web_cfg.get("auto_open_browser", True)

    if auto_open:
        url = f"http://{host}:{port}"
        try:
            webbrowser.open(url)
            success(f"Opened {url} in your browser")
        except Exception:
            info(f"Open {url} in your browser to use the Web UI")


def register(subs):
    p = subs.add_parser("web", help="Start the web UI on localhost")
    p.add_argument("port", nargs="?", type=int, default=None,
                   help="Port (default: from config)")
    p.set_defaults(func=cmd)


def cmd(args):
    config = load_config()
    web_cfg = config.get("web", {})
    host = web_cfg.get("host", "localhost")
    port = args.port or web_cfg.get("default_port", 1234)

    banner()
    _show_starting(port, host)
    _auto_open_browser(host, port)

    from http.server import HTTPServer

    try:
        from phox.web.server import PhoxHandler
        server = HTTPServer((host, port), PhoxHandler)
        server.serve_forever()
    except OSError as e:
        print()
        warning(f"Port {port} is already in use. Try a different port:")
        print(f"  phox web {port + 1}")
        print()
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        info("Shutting down web server...")
        success("Server stopped cleanly")
        print()
