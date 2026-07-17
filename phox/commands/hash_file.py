import hashlib
import os
from pathlib import Path

from phox.config import success, error, info, OUTPUT_DIR


def register(subs):
    p = subs.add_parser("hash-file", help="Hash a file")
    p.add_argument("file", help="File to hash")
    p.add_argument("-a", "--algo", default="sha256",
                   choices=["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"],
                   help="Algorithm (default: sha256)")
    p.add_argument("--all", dest="all_algos", action="store_true",
                   help="Hash with all algorithms")
    p.add_argument("-o", "--output", default=None,
                   help="Save hashes to file")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="Hash all files in directory recursively")
    p.set_defaults(func=cmd)


def hash_file(filepath, algo):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def cmd(args):
    filepath = Path(args.file)

    if not filepath.exists():
        error(f"File not found: {args.file}")
        return

    if filepath.is_dir():
        if not args.recursive:
            error(f"'{args.file}' is a directory. Use -r to hash recursively.")
            return
        files = sorted(filepath.rglob("*"))
        files = [f for f in files if f.is_file()]
        if not files:
            error(f"No files found in {args.file}")
            return

        info(f"Hashing {len(files)} files...")
        results = []
        for f in files:
            try:
                if args.all_algos:
                    hashes = {}
                    for algo in ["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"]:
                        hashes[algo] = hash_file(f, algo)
                    results.append({"file": str(f), "hashes": hashes})
                else:
                    h = hash_file(f, args.algo)
                    results.append({"file": str(f), "hash": h})
            except Exception as e:
                error(f"Failed: {f} - {e}")

        print()
        for r in results:
            fp = r["file"]
            if "hashes" in r:
                print(f"  {fp}")
                for algo, h in r["hashes"].items():
                    print(f"    {algo.upper():>10}: {h}")
            else:
                print(f"  {r['hash']:<64}  {fp}")
        print()

        if args.output:
            save_results(results, args.output, args.all_algos)
        return

    info(f"Hashing: {args.file} ({os.path.getsize(args.file):,} bytes)")

    if args.all_algos:
        print()
        for algo in ["md5", "sha1", "sha256", "sha512", "blake2b", "blake2s"]:
            h = hash_file(filepath, algo)
            print(f"  {algo.upper():>10}: {h}")
        print()
    else:
        h = hash_file(filepath, args.algo)
        print(f"  {args.algo.upper()}: {h}")
        print()

    if args.output:
        results = [{"file": str(filepath), "hash": h}]
        save_results(results, args.output, args.all_algos)


def save_results(results, output, all_algos):
    out_path = Path(output)
    if not out_path.is_absolute():
        out_path = OUTPUT_DIR / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            fp = r["file"]
            if "hashes" in r:
                for algo, h in r["hashes"].items():
                    f.write(f"{h}  {fp}  ({algo})\n")
            else:
                f.write(f"{r['hash']}  {fp}\n")

    success(f"Saved to {out_path}")
