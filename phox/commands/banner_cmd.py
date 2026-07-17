from phox.config import banner


def register(subs):
    p = subs.add_parser("banner", help="Display the PHOX ASCII art banner")
    p.set_defaults(func=cmd)


def cmd(args):
    banner()
