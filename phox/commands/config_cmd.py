import json
import os
import platform
import subprocess
import sys

from phox.config import (
    CONFIG_FILE, DEFAULT_CONFIG, SETTINGS_META,
    load_config, save_config, ensure_dirs,
    success, error, info, warning, c,
)


def _config_path():
    return str(CONFIG_FILE)


def _open_in_editor(path):
    if platform.system() == "Windows":
        os.startfile(path)
    else:
        editor = os.environ.get("EDITOR", "xdg-open")
        subprocess.Popen([editor, path])


def _get_nested(config, key):
    parts = key.split(".")
    obj = config
    for part in parts:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None
    return obj


def _set_nested(config, key, value):
    parts = key.split(".")
    obj = config
    for part in parts[:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value


def _type_coerce(value_str, meta=None):
    if meta and meta.get("type") == "bool":
        return value_str.lower() in ("true", "yes", "1")
    if meta and meta.get("type") == "int":
        return int(value_str)
    if value_str.lower() in ("true", "yes"):
        return True
    if value_str.lower() in ("false", "no"):
        return False
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


def _validate(key, value, meta):
    if not meta:
        return True, ""
    t = meta.get("type", "")
    if t == "int":
        if not isinstance(value, int):
            return False, f"Expected integer, got {type(value).__name__}"
        if "min" in meta and value < meta["min"]:
            return False, f"Value must be >= {meta['min']}"
        if "max" in meta and value > meta["max"]:
            return False, f"Value must be <= {meta['max']}"
    if t == "str" and "options" in meta:
        if value not in meta["options"]:
            return False, f"Must be one of: {', '.join(meta['options'])}"
    return True, ""


def register(subs):
    cfg = subs.add_parser("config", help="Manage Phox Tools configuration")
    cfg_sub = cfg.add_subparsers(dest="subcmd")

    p = cfg_sub.add_parser("list", help="Show all config settings and values")
    p.set_defaults(func=cmd_list)

    p = cfg_sub.add_parser("get", help="Get a specific config setting")
    p.add_argument("key", help="Setting key (e.g. web.default_port)")
    p.set_defaults(func=cmd_get)

    p = cfg_sub.add_parser("set", help="Set a config setting")
    p.add_argument("key", help="Setting key (e.g. web.default_port)")
    p.add_argument("value", help="New value")
    p.set_defaults(func=cmd_set)

    p = cfg_sub.add_parser("reset", help="Reset all config to defaults")
    p.set_defaults(func=cmd_reset)

    cfg.set_defaults(func=cmd_open)


def cmd_open(args):
    ensure_dirs()
    path = _config_path()
    if not os.path.exists(path):
        save_config(DEFAULT_CONFIG)
        info("Created default config file.")
    _open_in_editor(path)
    success(f"Opened config file: {path}")


def cmd_list(args):
    config = load_config()
    print()
    print(f"  {c('Config File:', 'bold')} {CONFIG_FILE}")
    print(f"  {c('─' * 50, 'muted')}")
    _print_dict(config, indent=2)
    print()


def _print_dict(d, indent=2, prefix=""):
    for key, value in d.items():
        full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            print(f"  {' ' * indent}{c(key + ':', 'bold')}")
            _print_dict(value, indent + 4, full_key)
        else:
            meta = SETTINGS_META.get(full_key, {})
            label = meta.get("label", key)
            print(f"  {' ' * indent}{label + ':':<30} {value}")


def cmd_get(args):
    config = load_config()
    value = _get_nested(config, args.key)
    if value is None and args.key not in config:
        error(f"Unknown setting: {args.key}")
        meta = SETTINGS_META.get(args.key)
        if meta:
            info(f"Label: {meta.get('label', '')}")
        return
    meta = SETTINGS_META.get(args.key, {})
    label = meta.get("label", args.key)
    print(f"\n  {c(label, 'bold')} = {value}")
    if meta.get("type"):
        info(f"Type: {meta['type']}")
    if "min" in meta or "max" in meta:
        range_str = f"Range: {meta.get('min', '-')} to {meta.get('max', '-')}"
        info(range_str)
    if "options" in meta:
        info(f"Options: {', '.join(meta['options'])}")
    print()


def cmd_set(args):
    config = load_config()
    meta = SETTINGS_META.get(args.key, {})

    existing = _get_nested(config, args.key)
    if existing is None and not meta:
        error(f"Unknown setting: {args.key}")
        info("Use 'phox config list' to see available settings.")
        return

    value = _type_coerce(args.value, meta)
    valid, msg = _validate(args.key, value, meta)
    if not valid:
        error(f"Invalid value: {msg}")
        return

    _set_nested(config, args.key, value)
    save_config(config)
    success(f"Set {args.key} = {value}")


def cmd_reset(args):
    save_config(DEFAULT_CONFIG.copy())
    success("Config reset to defaults.")
