import difflib
import sys
import argparse

from phox import __version__
from phox.config import banner, ensure_dirs, c, t

ALL_COMMANDS = []


class PhoxParser(argparse.ArgumentParser):

    def error(self, message):
        theme = t()

        if "invalid choice" in message:
            bad_cmd = ""
            if "'" in message:
                parts = message.split("'")
                if len(parts) >= 2:
                    bad_cmd = parts[1]

            print()
            print(
                f"  {theme['error']}[!]{theme['reset']} "
                f"Unknown command: {theme['bold']}{theme['primary']}{bad_cmd}{theme['reset']}"
            )

            if bad_cmd and ALL_COMMANDS:
                suggestions = difflib.get_close_matches(bad_cmd, ALL_COMMANDS, n=3, cutoff=0.4)
                if suggestions:
                    sugg_str = ", ".join(
                        f"{theme['primary']}{s}{theme['reset']}" for s in suggestions
                    )
                    print(f"  {theme['muted']}Did you mean:{theme['reset']}  {sugg_str}")
                else:
                    shown = ALL_COMMANDS[:6]
                    cmds_str = ", ".join(
                        f"{theme['primary']}{cmd}{theme['reset']}" for cmd in shown
                    )
                    print(f"  {theme['muted']}Available:{theme['reset']}     {cmds_str} ...")

            print()
            print(
                f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox help{theme['reset']}"
                f"{theme['muted']} to see all commands with descriptions{theme['reset']}"
            )
            print(
                f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox help <command>{theme['reset']}"
                f"{theme['muted']} for detailed usage{theme['reset']}"
            )
            print()
            sys.exit(2)

        if "expected one argument" in message:
            print()
            print(
                f"  {theme['error']}[!]{theme['reset']} "
                f"Missing required argument"
            )
            print(
                f"  {theme['muted']}{message}{theme['reset']}"
            )
            print(
                f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox help <command>{theme['reset']}"
                f"{theme['muted']} for usage details{theme['reset']}"
            )
            print()
            sys.exit(2)

        print()
        print(
            f"  {theme['error']}[!]{theme['reset']} "
            f"{message}"
        )
        print(
            f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox --help{theme['reset']}"
            f"{theme['muted']} for usage{theme['reset']}"
        )
        print()
        sys.exit(2)

    def print_usage(self, file=None):
        theme = t()
        usage = self.format_usage()
        print(
            f"\n  {theme['muted']}Usage:{theme['reset']} "
            f"{theme['bold']}phox{theme['reset']} "
            f"{theme['primary']}[command]{theme['reset']} "
            f"{theme['muted']}[options]{theme['reset']}"
        )


def main():
    ensure_dirs()

    try:
        _run()
    except KeyboardInterrupt:
        print()
        theme = t()
        print(
            f"  {theme['muted']}Interrupted.{theme['reset']}"
        )
        sys.exit(130)


def _run():
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        from phox.commands.help_cmd import cmd as help_cmd
        ns = argparse.Namespace()
        ns.command = sys.argv[1]
        ns.command_arg = sys.argv[2] if len(sys.argv) > 2 else None
        help_cmd(ns)
        sys.exit(0)

    parser = PhoxParser(
        prog="phox",
        description=None,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subs = parser.add_subparsers(dest="command")

    from phox.commands.cloner import register as reg_cloner
    from phox.commands.obfuscator import register as reg_obf
    from phox.commands.search import register as reg_search
    from phox.commands.encode_decode import register as reg_encdec
    from phox.commands.ip_lookup import register as reg_ip
    from phox.commands.dns_lookup import register as reg_dns
    from phox.commands.whois_lookup import register as reg_whois
    from phox.commands.username import register as reg_user
    from phox.commands.qr_code import register as reg_qr
    from phox.commands.api_request import register as reg_api
    from phox.commands.webhook import register as reg_webhook
    from phox.commands.theme_cmd import register as reg_theme
    from phox.commands.custom import register as reg_custom
    from phox.commands.serve import register as reg_web
    from phox.commands.hash_file import register as reg_hashfile
    from phox.commands.portscan import register as reg_portscan
    from phox.commands.subdomain import register as reg_subdomain
    from phox.commands.rand import register as reg_rand
    from phox.commands.colors import register as reg_colors
    from phox.commands.config_cmd import register as reg_config
    from phox.commands.banner_cmd import register as reg_banner

    for reg in [
        reg_cloner, reg_obf, reg_search, reg_encdec, reg_ip, reg_dns,
        reg_whois, reg_user, reg_qr, reg_api, reg_webhook, reg_theme,
        reg_custom, reg_web, reg_hashfile, reg_portscan, reg_subdomain,
        reg_rand, reg_colors, reg_config, reg_banner,
    ]:
        reg(subs)

    global ALL_COMMANDS
    ALL_COMMANDS = sorted(subs.choices.keys())

    args = parser.parse_args()

    if args.command is None:
        banner()
        theme = t()
        print(
            f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox help{theme['reset']}"
            f"{theme['muted']} for available commands{theme['reset']}"
        )
        print()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        theme = t()
        print()
        print(
            f"  {theme['error']}[!]{theme['reset']} "
            f"Unknown command: {theme['bold']}{args.command}{theme['reset']}"
        )
        print(
            f"  {theme['muted']}Run {theme['bold']}{theme['primary']}phox help{theme['reset']}"
            f"{theme['muted']} to see available commands{theme['reset']}"
        )
        print()


if __name__ == "__main__":
    main()
