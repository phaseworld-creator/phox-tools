import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path

from phox.config import COMMANDS_DIR, ensure_dirs, success, error, info

COMMAND_TEMPLATE = '''"""
Custom Phox command: {name}
Created: {date}
Edit this file to customize your command.
"""

import click


@click.command("{name}")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def {func_name}(verbose):
    """{description}"""
    if verbose:
        print("Running custom command: {name}")

    print("Hello from custom command: {name}!")
    print("Edit this file to change what this does.")


COMMAND = {func_name}
'''


def _init_file():
    init = COMMANDS_DIR / "__init__.py"
    if not init.exists():
        COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        init.write_text("# Custom Phox commands\n")


def _cmd_file(name):
    safe = name.replace("-", "_").replace(" ", "_").replace(".", "_")
    return COMMANDS_DIR / f"{safe}.py"


def register(subs):
    cu = subs.add_parser("custom", help="Manage custom commands")
    cu_sub = cu.add_subparsers(dest="subcmd")

    p = cu_sub.add_parser("new", help="Create a new custom command")
    p.add_argument("name")
    p.add_argument("-d", "--description", default="")
    p.set_defaults(func=cmd_new)

    p = cu_sub.add_parser("list", help="List custom commands")
    p.set_defaults(func=cmd_list)

    p = cu_sub.add_parser("run", help="Run a custom command")
    p.add_argument("name")
    p.add_argument("args", nargs="*")
    p.set_defaults(func=cmd_run)

    p = cu_sub.add_parser("edit", help="Show edit path for a command")
    p.add_argument("name")
    p.set_defaults(func=cmd_edit)

    p = cu_sub.add_parser("delete", help="Delete a custom command")
    p.add_argument("name")
    p.set_defaults(func=cmd_delete)

    p = cu_sub.add_parser("share", help="Show how to share commands")
    p.set_defaults(func=cmd_share)

    cu.set_defaults(func=cmd_custom_help)


def cmd_custom_help(args):
    print("""
  Custom Commands
  Create and manage your own reusable Phox commands

  Usage:
    phox custom <command> [options]

  Commands:
    new <name> [-d DESC]   Create a new custom command
    list                   List all custom commands
    run <name> [args...]   Run a custom command
    edit <name>            Open command file for editing
    delete <name>          Delete a custom command
    share                  Show how to share commands

  Examples:
    phox custom new my-tool -d "My awesome tool"
    phox custom list
    phox custom run my-tool
    phox custom delete my-tool
""")


def cmd_new(args):
    _init_file()
    fp = _cmd_file(args.name)
    if fp.exists():
        error(f"Command '{args.name}' already exists at {fp}")
        return

    func_name = args.name.replace("-", "_").replace(" ", "_").replace(".", "_")
    content = COMMAND_TEMPLATE.format(
        name=args.name, func_name=func_name,
        description=args.description or f"Custom command: {args.name}",
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    fp.write_text(content, encoding="utf-8")
    success(f"Created '{args.name}' at {fp}")


def cmd_list(args):
    _init_file()
    files = sorted(COMMANDS_DIR.glob("*.py"))
    if not files:
        info("No custom commands. Create one with 'phox custom new <name>'")
        return
    print()
    for f in files:
        if f.name.startswith("_"):
            continue
        desc = ""
        try:
            for line in f.read_text(encoding="utf-8").split("\n"):
                stripped = line.strip()
                if stripped.startswith('"""') and not stripped.endswith('"""'):
                    desc = stripped.strip('"')
                    break
        except Exception:
            pass
        print(f"  {f.stem:>20}  {desc or 'Custom command'}")
    print()


def cmd_run(args):
    fp = _cmd_file(args.name)
    if not fp.exists():
        error(f"Command '{args.name}' not found at {fp}")
        return

    info(f"Running: {args.name}")
    try:
        spec = importlib.util.spec_from_file_location(args.name, str(fp))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "COMMAND"):
            cmd = module.COMMAND
            cmd(args=args.args, standalone_mode=False)
        else:
            error(f"No COMMAND found in {fp}")
    except SystemExit:
        pass
    except Exception as e:
        error(f"Failed: {e}")


def cmd_edit(args):
    fp = _cmd_file(args.name)
    if not fp.exists():
        error(f"Command '{args.name}' not found at {fp}")
        return
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if editor:
        os.system(f'{editor} "{fp}"')
    else:
        info(f"Edit file: {fp}")


def cmd_delete(args):
    fp = _cmd_file(args.name)
    if not fp.exists():
        error(f"Command '{args.name}' not found")
        return
    fp.unlink()
    success(f"Deleted '{args.name}'")


def cmd_share(args):
    print()
    print(f"  Custom Commands Directory:")
    print(f"  {COMMANDS_DIR}")
    print()
    print(f"  To share:")
    print(f"  1. Copy .py files from {COMMANDS_DIR}")
    print(f"  2. Place in the other user's ~/.phox/commands/")
    print(f"  3. They run: phox custom list")
    print()
