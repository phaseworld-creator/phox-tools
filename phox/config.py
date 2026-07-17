import io
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

PHOX_DIR = Path.home() / ".phox"
COMMANDS_DIR = PHOX_DIR / "commands"
THEMES_DIR = PHOX_DIR / "themes"

if sys.platform == "win32":
    CONFIG_FILE = Path(os.environ.get("APPDATA", str(Path.home()))) / "PHOX Tools" / "config.json"
else:
    CONFIG_FILE = PHOX_DIR / "config.json"

if sys.platform == "win32":
    OUTPUT_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "PHOX Tools" / "output"
else:
    OUTPUT_DIR = PHOX_DIR / "output"
CLONED_DIR = OUTPUT_DIR / "cloned"

DEFAULT_THEME = {
    "name": "default",
    "primary": "\033[96m",
    "secondary": "\033[93m",
    "success": "\033[92m",
    "error": "\033[91m",
    "warning": "\033[93m",
    "info": "\033[94m",
    "muted": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
    "banner_color": "\033[95m",
}

DEFAULT_CONFIG = {
    "active_theme": "default",
    "custom_webhooks": [],
    "web": {
        "default_port": 1234,
        "host": "localhost",
        "auto_open_browser": True,
        "keep_running": True,
    },
    "cloner": {
        "max_depth": 5,
        "concurrency": 10,
        "respect_robots": True,
        "delay": 0.1,
    },
    "output": {
        "auto_save": True,
        "format": "json",
    },
    "general": {
        "check_updates": True,
        "verbose_errors": False,
    },
}

SETTINGS_META = {
    "web.default_port": {"type": "int", "label": "Default Web Port", "min": 1, "max": 65535},
    "web.host": {"type": "str", "label": "Web Host", "options": ["localhost", "0.0.0.0", "127.0.0.1"]},
    "web.auto_open_browser": {"type": "bool", "label": "Auto-Open Browser"},
    "web.keep_running": {"type": "bool", "label": "Keep Web Dashboard Running"},
    "cloner.max_depth": {"type": "int", "label": "Cloner Max Depth", "min": 1, "max": 20},
    "cloner.concurrency": {"type": "int", "label": "Cloner Concurrency", "min": 1, "max": 50},
    "output.auto_save": {"type": "bool", "label": "Auto-Save Results"},
    "general.check_updates": {"type": "bool", "label": "Check for Updates"},
    "general.verbose_errors": {"type": "bool", "label": "Verbose Errors"},
}


def ensure_dirs():
    PHOX_DIR.mkdir(parents=True, exist_ok=True)
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CLONED_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
            config = {**DEFAULT_CONFIG, **saved}
            return config
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    ensure_dirs()
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_theme(name=None):
    ensure_dirs()
    config = load_config()
    name = name or config.get("active_theme", "default")

    theme_file = THEMES_DIR / f"{name}.json"
    if theme_file.exists():
        with open(theme_file) as f:
            base = DEFAULT_THEME.copy()
            base.update(json.load(f))
            return base
    return DEFAULT_THEME.copy()


def save_theme(theme_data):
    ensure_dirs()
    name = theme_data.get("name", "custom")
    theme_file = THEMES_DIR / f"{name}.json"
    with open(theme_file, "w", encoding="utf-8") as f:
        json.dump(theme_data, f, indent=2)


def list_themes():
    ensure_dirs()
    themes = []
    for f in THEMES_DIR.glob("*.json"):
        themes.append(f.stem)
    if "default" not in themes:
        themes.insert(0, "default")
    return themes


_theme = None


def t():
    global _theme
    if _theme is None:
        _theme = load_theme()
    return _theme


def reset_theme():
    global _theme
    _theme = None


def c(text, color_key):
    theme = t()
    color = theme.get(color_key, "")
    reset = theme.get("reset", "")
    return f"{color}{text}{reset}"


def banner():
    theme = t()
    b = f"""
{theme['banner_color']}{theme['bold']}
██████╗ ██╗  ██╗ ██████╗ ██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗╚██╗██╔╝
██████╔╝███████║██║   ██║ ╚███╔╝ 
██╔═══╝ ██╔══██║██║   ██║ ██╔██╗ 
██║     ██║  ██║╚██████╔╝██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝{theme['reset']}
{theme['muted']}  ── Swiss Army Knife for Hackers ──{theme['reset']}
"""
    print(b)


def success(msg):
    print(f"{t()['success']}[+]{t()['reset']} {msg}")


def error(msg):
    print(f"{t()['error']}[!]{t()['reset']} {msg}")


def info(msg):
    print(f"{t()['info']}[*]{t()['reset']} {msg}")


def warning(msg):
    print(f"{t()['warning']}[~]{t()['reset']} {msg}")


def p(color_key, text):
    print(c(text, color_key))
