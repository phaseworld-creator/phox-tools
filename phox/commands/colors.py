import sys
from phox.config import t


def register(subs):
    p = subs.add_parser("colors", help="Display terminal color palette")
    p.add_argument("--test", action="store_true",
                   help="Run color compatibility test")
    p.set_defaults(func=cmd)


def cmd(args):
    theme = t()
    r = theme.get("reset", "\033[0m")

    if args.test:
        run_test()
        return

    print()

    colors = [
        ("Black",   "\033[30m"),
        ("Red",     "\033[31m"),
        ("Green",   "\033[32m"),
        ("Yellow",  "\033[33m"),
        ("Blue",    "\033[34m"),
        ("Magenta", "\033[35m"),
        ("Cyan",    "\033[36m"),
        ("White",   "\033[37m"),
    ]

    bright_colors = [
        ("Bright Red",     "\033[91m"),
        ("Bright Green",   "\033[92m"),
        ("Bright Yellow",  "\033[93m"),
        ("Bright Blue",    "\033[94m"),
        ("Bright Magenta", "\033[95m"),
        ("Bright Cyan",    "\033[96m"),
        ("Bright White",   "\033[97m"),
    ]

    styles = [
        ("Bold",       "\033[1m"),
        ("Dim",        "\033[2m"),
        ("Underline",  "\033[4m"),
        ("Blink",      "\033[5m"),
        ("Reverse",    "\033[7m"),
        ("Strikethrough", "\033[9m"),
    ]

    print("  Standard Colors")
    print("  " + "─" * 40)
    for name, code in colors:
        print(f"  {code}████████{r}  {name}")

    print()
    print("  Bright Colors")
    print("  " + "─" * 40)
    for name, code in bright_colors:
        print(f"  {code}████████{r}  {name}")

    print()
    print("  256-Color Palette")
    print("  " + "─" * 40)
    for row in range(0, 16):
        line = "  "
        for col in range(0, 16):
            idx = row * 16 + col
            line += f"\033[48;5;{idx}m  {idx:>3}  {r}"
        print(line)

    print()
    print("  Styles (using theme primary)")
    print("  " + "─" * 40)
    primary = theme.get("primary", "\033[96m")
    for name, code in styles:
        print(f"  {code}{primary}{'The quick brown fox':.<30}{r}  {name}")

    print()
    print("  Theme Colors")
    print("  " + "─" * 40)
    for key in ["primary", "secondary", "success", "error", "warning", "info",
                "muted", "banner_color"]:
        val = theme.get(key, "")
        print(f"  {val}████████{r}  {key}")

    print()


def run_test():
    print()
    print("  Color Test")
    print("  " + "─" * 40)

    tests = [
        ("Reset",         "\033[0m"),
        ("Bold",          "\033[1m"),
        ("Red text",      "\033[91m"),
        ("Green text",    "\033[92m"),
        ("Yellow text",   "\033[93m"),
        ("Blue text",     "\033[94m"),
        ("Magenta text",  "\033[95m"),
        ("Cyan text",     "\033[96m"),
        ("256-color",     "\033[48;5;208m\033[30m"),
        ("TrueColor",     "\033[48;2;255;100;0m\033[30m"),
    ]

    r = "\033[0m"
    for name, code in tests:
        print(f"  {code}{name}: if you can read this{r}  OK")

    print()
    encoding = getattr(sys.stdout, "encoding", "unknown")
    print(f"  Terminal encoding: {encoding}")
    platform = sys.platform
    print(f"  Platform: {platform}")
    print()

    if "256" in encoding.lower() or "utf" in encoding.lower():
        from phox.config import success
        success("Your terminal supports colors!")
    else:
        from phox.config import warning
        warning("Your terminal may have limited color support")
        print(f"    Try: set PYTHONIOENCODING=utf-8")
    print()
