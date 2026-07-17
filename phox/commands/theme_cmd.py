import json

from phox.config import (
    load_theme, save_theme, list_themes, load_config, save_config,
    reset_theme, DEFAULT_THEME, THEMES_DIR,
    success, error, info, c,
)


def register(subs):
    th = subs.add_parser("theme", help="Customize Phox appearance")
    th_sub = th.add_subparsers(dest="subcmd")

    p = th_sub.add_parser("list", help="List available themes")
    p.set_defaults(func=cmd_list)

    p = th_sub.add_parser("set", help="Set active theme")
    p.add_argument("name")
    p.set_defaults(func=cmd_set)

    p = th_sub.add_parser("show", help="Show theme colors")
    p.add_argument("name", nargs="?", default=None)
    p.set_defaults(func=cmd_show)

    p = th_sub.add_parser("preset", help="Apply a preset theme")
    p.add_argument("name",
                   choices=["hacker", "ocean", "sunset", "matrix", "cyberpunk"])
    p.set_defaults(func=cmd_preset)

    p = th_sub.add_parser("create", help="Create a custom theme")
    p.add_argument("name")
    p.set_defaults(func=cmd_create)

    p = th_sub.add_parser("reset", help="Reset to default theme")
    p.set_defaults(func=cmd_reset)

    th.set_defaults(func=cmd_theme_help)


def cmd_theme_help(args):
    print("""
  Theme Customizer
  Change colors and appearance of Phox terminal UI

  Usage:
    phox theme <command> [options]

  Commands:
    list                    List available themes
    set <name>              Set active theme
    show [name]             Show theme colors
    preset <name>           Apply a preset theme
    create <name>           Create a custom theme interactively
    reset                   Reset to default theme

  Presets: hacker, ocean, sunset, matrix, cyberpunk

  Examples:
    phox theme preset matrix
    phox theme list
    phox theme show
    phox theme create mytheme
""")


def cmd_list(args):
    themes = list_themes()
    config = load_config()
    active = config.get("active_theme", "default")
    print()
    for t in themes:
        marker = " (active)" if t == active else ""
        print(f"  {t}{marker}")
    print()


def cmd_set(args):
    themes = list_themes()
    if args.name not in themes:
        error(f"Theme '{args.name}' not found. Available: {', '.join(themes)}")
        return
    config = load_config()
    config["active_theme"] = args.name
    save_config(config)
    reset_theme()
    success(f"Theme set to '{args.name}'")


def cmd_show(args):
    t = load_theme(args.name)
    name = args.name or load_config().get("active_theme", "default")
    print(f"\n  Theme: {name}\n")
    for key, value in t.items():
        if key in ("reset", "bold"):
            continue
        print(f"  {key + ':':>20} {value}")
    print()


def cmd_preset(args):
    presets = {
        "hacker": {
            "name": "hacker",
            "primary": "\033[92m", "secondary": "\033[93m",
            "success": "\033[92m", "error": "\033[91m",
            "warning": "\033[93m", "info": "\033[92m",
            "muted": "\033[90m", "banner_color": "\033[92m",
        },
        "ocean": {
            "name": "ocean",
            "primary": "\033[96m", "secondary": "\033[94m",
            "success": "\033[92m", "error": "\033[91m",
            "warning": "\033[93m", "info": "\033[94m",
            "muted": "\033[90m", "banner_color": "\033[94m",
        },
        "sunset": {
            "name": "sunset",
            "primary": "\033[91m", "secondary": "\033[93m",
            "success": "\033[92m", "error": "\033[91m",
            "warning": "\033[93m", "info": "\033[95m",
            "muted": "\033[90m", "banner_color": "\033[91m",
        },
        "matrix": {
            "name": "matrix",
            "primary": "\033[32m", "secondary": "\033[92m",
            "success": "\033[92m", "error": "\033[91m",
            "warning": "\033[93m", "info": "\033[32m",
            "muted": "\033[90m", "banner_color": "\033[92m",
        },
        "cyberpunk": {
            "name": "cyberpunk",
            "primary": "\033[95m", "secondary": "\033[96m",
            "success": "\033[92m", "error": "\033[91m",
            "warning": "\033[93m", "info": "\033[95m",
            "muted": "\033[90m", "banner_color": "\033[95m",
        },
    }
    save_theme(presets[args.name])
    config = load_config()
    config["active_theme"] = args.name
    save_config(config)
    reset_theme()
    success(f"Preset '{args.name}' applied!")


def cmd_create(args):
    theme_data = DEFAULT_THEME.copy()
    theme_data["name"] = args.name
    print(f"Creating theme '{args.name}' (based on default)")
    print("Enter ANSI color codes (or Enter to keep default):\n")
    for key in ["primary", "secondary", "success", "error",
                "warning", "info", "muted", "banner_color"]:
        current = theme_data.get(key, "")
        default_display = current.replace("\033", "\\033") if current else "none"
        new_val = input(f"  {key} [{default_display}]: ").strip()
        if new_val:
            if new_val.isdigit():
                theme_data[key] = f"\033[{new_val}m"
            elif new_val.startswith("\\033"):
                theme_data[key] = new_val.replace("\\033", "\033")
            else:
                theme_data[key] = new_val
    save_theme(theme_data)
    success(f"Theme '{args.name}' created! Use 'phox theme set {args.name}'")


def cmd_reset(args):
    config = load_config()
    config["active_theme"] = "default"
    save_config(config)
    reset_theme()
    success("Theme reset to default")
