import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from phox.config import success, error, info, OUTPUT_DIR, warning, c, t


def _api_generate(text, size=300):
    encoded = urllib.parse.quote(text, safe="")
    url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}&format=svg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Phox/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return None


def _local_generate(text):
    from phox.lib.qr import generate, to_svg
    matrix = generate(text)
    return to_svg(matrix)


def _bold(text):
    return c(text, "bold")


def _primary(text):
    return c(text, "primary")


def _muted(text):
    return c(text, "muted")


def register(subs):
    p = subs.add_parser("qr", help="Generate QR codes")
    p.add_argument("text", help="Text or URL to encode")
    p.add_argument("-o", "--output", default=None,
                   help="Output file (default: qr_output.svg)")
    p.add_argument("-s", "--size", type=int, default=300,
                   help="Image size in pixels (default: 300)")
    p.add_argument("--format", dest="fmt", default="svg",
                   choices=["svg", "png", "txt"],
                   help="Output format (default: svg)")
    p.add_argument("--local", action="store_true",
                   help="Force local generation (no API)")
    p.set_defaults(func=cmd)


def cmd(args):
    text = args.text
    output = args.output
    if output is None:
        ext = "svg" if args.fmt != "txt" else "txt"
        output = str(OUTPUT_DIR / f"qr_output.{ext}")
    else:
        p = Path(output)
        if not p.is_absolute():
            output = str(OUTPUT_DIR / p.name)

    theme = t()
    display_text = text[:50] + "..." if len(text) > 50 else text

    info(f"Generating QR for: {display_text}")

    fmt_labels = {
        "svg": "SVG (vector)",
        "png": "PNG (raster image)",
        "txt": "TXT (terminal art)",
    }
    info(f"Format: {fmt_labels.get(args.fmt, args.fmt)}  |  Size: {args.size}px")
    if args.fmt == "txt":
        try:
            from phox.lib.qr import generate, to_text
            matrix = generate(text)
            print()
            print(to_text(matrix))
            print()
            success("QR code printed to terminal")
            _show_format_tip("txt")
        except Exception as e:
            error(f"Text generation failed: {e}")
        return
    svg_content = None
    source = None
    if not args.local:
        svg_content = _api_generate(text, size=args.size)
        if svg_content:
            source = "QR Server API"

    if not svg_content:
        if not args.local:
            warning("API unavailable, falling back to local generator")
        try:
            svg_content = _local_generate(text)
            source = "Local generator"
        except Exception as e:
            error(f"QR generation failed: {e}")
            return

    info(f"Generated via: {source}")
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.fmt == "png" and source == "QR Server API":
        encoded = urllib.parse.quote(text, safe="")
        png_url = f"https://api.qrserver.com/v1/create-qr-code/?size={args.size}x{args.size}&data={encoded}&format=png"
        try:
            req = urllib.request.Request(png_url, headers={"User-Agent": "Phox/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                png_data = resp.read()
            out_path = out_path.with_suffix(".png")
            with open(out_path, "wb") as f:
                f.write(png_data)
            _show_saved("PNG", out_path)
        except Exception as e:
            error(f"PNG download failed: {e}")
            out_path = out_path.with_suffix(".svg")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            _show_saved("SVG (PNG fallback)", out_path)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        _show_saved("SVG", out_path)

    _show_format_tip(args.fmt)


def _show_saved(fmt, path):
    theme = t()
    print()
    print(f"  {theme['success']}[+]{theme['reset']} "
          f"{_muted(fmt + ' saved to')}")
    print(f"  {_primary(str(path))}")
    print()


def _show_format_tip(fmt):
    theme = t()
    tips = {
        "svg": "Open in a browser or vector editor to view. Scales to any size.",
        "png": "Raster image - ready to use in documents, emails, or web pages.",
        "txt": "Text QR is best for terminal use and quick sharing.",
    }
    tip = tips.get(fmt)
    if tip:
        print(f"  {theme['muted']}Tip: {tip}{theme['reset']}")
        print()
