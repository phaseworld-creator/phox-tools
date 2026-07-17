import base64
import secrets
import string
import sys

from phox.config import success, error, info


def register(subs):
    p = subs.add_parser("rand", help="Generate random data")
    p.add_argument("-n", "--count", type=int, default=1,
                   help="Number of items (default: 1)")
    p.add_argument("-t", "--type", dest="rtype", default="string",
                   choices=["string", "number", "hex", "bytes", "uuid", "ip",
                            "password", "dice", "coin", "choice"],
                   help="Type of random data (default: string)")
    p.add_argument("-l", "--length", type=int, default=16,
                   help="Length for string/hex/bytes (default: 16)")
    p.add_argument("--min", type=int, default=1,
                   help="Min for number type (default: 1)")
    p.add_argument("--max", type=int, default=100,
                   help="Max for number type (default: 100)")
    p.add_argument("--sides", type=int, default=6,
                   help="Dice sides (default: 6)")
    p.add_argument("--options", nargs="+",
                   help="Options for choice type")
    p.add_argument("--no-special", action="store_true",
                   help="Exclude special chars in password")
    p.add_argument("--no-upper", action="store_true",
                   help="Exclude uppercase in password")
    p.add_argument("--no-digits", action="store_true",
                   help="Exclude digits in password")
    p.set_defaults(func=cmd)


def gen_string(length):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def gen_number(min_val, max_val):
    return secrets.randbelow(max_val - min_val + 1) + min_val


def gen_hex(length):
    return secrets.token_hex(length)


def gen_bytes(length):
    return base64.b64encode(secrets.token_bytes(length)).decode()


def gen_uuid():
    h = secrets.token_hex(16)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def gen_ip():
    return f"{secrets.randbelow(223)+1}.{secrets.randbelow(256)}.{secrets.randbelow(256)}.{secrets.randbelow(256)}"


def gen_password(length, no_special=False, no_upper=False, no_digits=False):
    chars = string.ascii_lowercase
    if not no_upper:
        chars += string.ascii_uppercase
    if not no_digits:
        chars += string.digits
    if not no_special:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    pw = list(secrets.choice(chars) for _ in range(length))
    if not no_upper:
        pw[0] = secrets.choice(string.ascii_uppercase)
    if not no_digits:
        pw[1] = secrets.choice(string.digits)
    if not no_special:
        pw[2] = secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?")
    import random
    random.SystemRandom().shuffle(pw)
    return "".join(pw)


def gen_dice(sides):
    return secrets.randbelow(sides) + 1


def gen_coin():
    return secrets.choice(["Heads", "Tails"])


def gen_choice(options):
    return secrets.choice(options)


def cmd(args):
    n = max(args.count, 1)

    print()
    for i in range(n):
        if args.rtype == "string":
            val = gen_string(args.length)
        elif args.rtype == "number":
            val = gen_number(args.min, args.max)
        elif args.rtype == "hex":
            val = gen_hex(args.length)
        elif args.rtype == "bytes":
            val = gen_bytes(args.length)
        elif args.rtype == "uuid":
            val = gen_uuid()
        elif args.rtype == "ip":
            val = gen_ip()
        elif args.rtype == "password":
            val = gen_password(args.length, args.no_special,
                               args.no_upper, args.no_digits)
        elif args.rtype == "dice":
            val = f"{gen_dice(args.sides)} (d{args.sides})"
        elif args.rtype == "coin":
            val = gen_coin()
        elif args.rtype == "choice":
            if not args.options:
                error("Use --options to specify choices")
                return
            val = gen_choice(args.options)
        else:
            val = "?"

        if n == 1:
            print(f"  {val}")
        else:
            print(f"  {i+1:>3}. {val}")

    print()
