import base64
import hashlib
import json
import secrets
import string
import sys
import urllib.parse

from phox.config import success, error, info, c, t


def _label(text):
    return c(text, "bold")


def _result(text):
    return c(text, "primary")


def _algo_name(text):
    return c(text, "info")


def _hash_val(text):
    return c(text, "warning")


def _muted(text):
    return c(text, "muted")


def _success(text):
    return c(text, "success")


def register(subs):
    enc = subs.add_parser("encode", help="Encode text in various formats")
    enc_sub = enc.add_subparsers(dest="encoding")

    p = enc_sub.add_parser("base64", help="Base64 encode")
    p.add_argument("text")
    p.set_defaults(func=cmd_encode_b64)

    p = enc_sub.add_parser("hex", help="Hex encode")
    p.add_argument("text")
    p.set_defaults(func=cmd_encode_hex)

    p = enc_sub.add_parser("url", help="URL encode")
    p.add_argument("text")
    p.set_defaults(func=cmd_encode_url)

    dec = subs.add_parser("decode", help="Decode text in various formats")
    dec_sub = dec.add_subparsers(dest="encoding")

    p = dec_sub.add_parser("base64", help="Base64 decode")
    p.add_argument("text")
    p.set_defaults(func=cmd_decode_b64)

    p = dec_sub.add_parser("hex", help="Hex decode")
    p.add_argument("text")
    p.set_defaults(func=cmd_decode_hex)

    p = dec_sub.add_parser("url", help="URL decode")
    p.add_argument("text")
    p.set_defaults(func=cmd_decode_url)

    HASH_ALGOS = ["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"]

    p = subs.add_parser("hash", help="Hash text")
    p.add_argument("text")
    p.add_argument("-a", "--algo", default="sha256",
                   choices=HASH_ALGOS, help="Algorithm (default: sha256)")
    p.set_defaults(func=cmd_hash)

    p = subs.add_parser("hash-all", help="Hash with all algorithms")
    p.add_argument("text")
    p.set_defaults(func=cmd_hash_all)

    p = subs.add_parser("password", help="Generate secure passwords")
    p.add_argument("-l", "--length", type=int, default=16,
                   help="Length (default: 16)")
    p.add_argument("-n", "--count", type=int, default=1,
                   help="Number of passwords")
    p.add_argument("--no-special", action="store_true")
    p.add_argument("--no-digits", action="store_true")
    p.add_argument("--no-upper", action="store_true")
    p.set_defaults(func=cmd_password)


def cmd_encode_b64(args):
    result = base64.b64encode(args.text.encode()).decode()
    print()
    print(f"  {_label('Base64 Encode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()


def cmd_encode_hex(args):
    result = args.text.encode().hex()
    print()
    print(f"  {_label('Hex Encode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()


def cmd_encode_url(args):
    result = urllib.parse.quote(args.text, safe="")
    print()
    print(f"  {_label('URL Encode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()


def cmd_decode_b64(args):
    try:
        result = base64.b64decode(args.text.encode()).decode()
    except Exception as e:
        error(f"Invalid Base64: {e}")
        return
    print()
    print(f"  {_label('Base64 Decode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()


def cmd_decode_hex(args):
    try:
        result = bytes.fromhex(args.text).decode()
    except Exception as e:
        error(f"Invalid hex: {e}")
        return
    print()
    print(f"  {_label('Hex Decode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()


def cmd_decode_url(args):
    result = urllib.parse.unquote(args.text)
    print()
    print(f"  {_label('URL Decode')}")
    print(f"  {_muted('─' * 40)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Output:')} {c(result, 'primary')}")
    print()

HASH_ALGOS = ["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"]


def _compute_hash(algo, text):
    h = hashlib.new(algo)
    h.update(text.encode())
    return h.hexdigest()


def cmd_hash(args):
    digest = _compute_hash(args.algo, args.text)
    algo_label = args.algo.upper()
    print()
    print(f"  {_label('Hash')}")
    print(f"  {_muted('─' * 50)}")
    print(f"  {_success('Algo:')}   {_algo_name(algo_label)}")
    print(f"  {_success('Input:')}  {args.text}")
    print(f"  {_success('Digest:')} {_hash_val(digest)}")
    print()


def cmd_hash_all(args):
    print()
    print(f"  {_label('Hash All Algorithms')}")
    print(f"  {_muted('─' * 60)}")
    print(
        f"  {_success('Input:')}  {args.text}"
    )
    print(f"  {_muted('─' * 60)}")

    max_algo_len = max(len(a.upper()) for a in HASH_ALGOS)

    for algo in HASH_ALGOS:
        digest = _compute_hash(algo, args.text)
        algo_display = algo.upper().rjust(max_algo_len)
        print(f"  {_algo_name(algo_display)}  {_hash_val(digest)}")

    print(f"  {_muted('─' * 60)}")
    print(f"  {_muted(f'{len(HASH_ALGOS)} algorithms computed')}")
    print()

def cmd_password(args):
    chars = string.ascii_lowercase
    if not args.no_upper:
        chars += string.ascii_uppercase
    if not args.no_digits:
        chars += string.digits
    if not args.no_special:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    length = max(args.length, 4)

    print()
    print(f"  {_label('Generated Passwords')}")
    print(f"  {_muted('─' * 50)}")
    print(
        f"  {_muted('Length:')} {_success(str(length))}"
        f"  {_muted('|')}"
        f"  {_muted('Count:')} {_success(str(args.count))}"
    )
    print(f"  {_muted('─' * 50)}")

    for i in range(args.count):
        pw = [secrets.choice(chars) for _ in range(length)]
        if not args.no_upper:
            pw[0] = secrets.choice(string.ascii_uppercase)
        if not args.no_digits:
            pw[1] = secrets.choice(string.digits)
        if not args.no_special:
            pw[2] = secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?")
        # Shuffle
        import random
        random.SystemRandom().shuffle(pw)
        password = "".join(pw)
        print(f"  {c(password, 'primary')}  {_muted(f'({length} chars)')}")

    print(f"  {_muted('─' * 50)}")
    print()
