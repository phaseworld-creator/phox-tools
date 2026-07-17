import ast
import base64
import random
import string
import sys
from pathlib import Path
from textwrap import dedent

from phox.config import success, error, info, OUTPUT_DIR


def random_name(length=16):
    return "_" + "".join(random.choices(string.ascii_letters, k=length))


def encrypt_string(s):
    key = random.randint(1, 255)
    encoded = bytes([b ^ key for b in s.encode("utf-8")])
    b64 = base64.b64encode(encoded).decode()
    return b64, key


def generate_junk_code():
    templates = [
        lambda: f"{random_name()} = {random.randint(0, 9999)}",
        lambda: f"{random_name()} = {random.choice(['True', 'False'])}",
        lambda: f"{random_name()} = '{random_name(8)}'",
        lambda: f"{random_name()} = [None] * {random.randint(1, 10)}",
        lambda: f"if {random.choice(['True', 'False'])}:\n    pass",
    ]
    return "\n".join(random.choice(templates)() for _ in range(random.randint(2, 5)))


class StringEncryptor(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) > 2:
            b64, key = encrypt_string(node.value)
            return ast.Call(
                func=ast.Name(id="__px_dec", ctx=ast.Load()),
                args=[ast.Constant(value=b64), ast.Constant(value=key)],
                keywords=[],
            )
        return node


DECRYPTOR = dedent('''
def __px_dec(data, key):
    import base64 as _b64
    return bytes([b ^ key for b in _b64.b64decode(data)]).decode()
''').strip()


def obfuscate_code(source, layers=1, junk=True):
    for layer in range(layers):
        info(f"Processing layer {layer + 1}/{layers}...")
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            error(f"Syntax error: {e}")
            return source

        transformer = StringEncryptor()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        try:
            source = ast.unparse(new_tree)
        except Exception:
            pass

        source = DECRYPTOR + "\n\n" + source

        if junk:
            lines = source.split("\n")
            new_lines = []
            block_openers = ('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')
            for i, line in enumerate(lines):
                new_lines.append(line)
                stripped = line.strip()
                indent = len(line) - len(line.lstrip()) if stripped else 0
                if indent != 0:
                    continue
                if stripped == '' or stripped.endswith(':'):
                    continue
                if any(stripped.startswith(b) for b in block_openers):
                    continue
                if random.random() < 0.3:
                    new_lines.append(generate_junk_code())
            source = "\n".join(new_lines)

    return source


def register(subs):
    p = subs.add_parser("obfuscate", help="Obfuscate a Python file")
    p.add_argument("input_file", help="Python file to obfuscate")
    p.add_argument("-o", "--output", default=None,
                   help="Output file (default: <input>_obfuscated.py)")
    p.add_argument("-l", "--layers", type=int, default=1,
                   help="Obfuscation layers (default: 1)")
    p.add_argument("--no-junk", action="store_true",
                   help="Don't insert junk code")
    p.set_defaults(func=cmd)


def cmd(args):
    output = args.output
    if output is None:
        base = args.input_file.rsplit(".", 1)[0]
        output = str(OUTPUT_DIR / f"{base}_obfuscated.py")
    else:
        from pathlib import Path as _P
        p = _P(output)
        if not p.is_absolute():
            output = str(OUTPUT_DIR / p.name)

    info(f"Reading {args.input_file}...")
    with open(args.input_file, "r", encoding="utf-8") as f:
        source = f.read()

    result = obfuscate_code(source, layers=args.layers, junk=not args.no_junk)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(result)

    success(f"Obfuscated -> {output} (layers={args.layers})")
