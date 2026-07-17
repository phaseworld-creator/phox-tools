import io
import os
import sys
import shutil
import subprocess
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )



GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
MUTED  = "\033[90m"
RESET  = "\033[0m"


def ok(msg):    print(f"  {GREEN}[+]{RESET} {msg}")
def fail(msg):  print(f"  {RED}[!]{RESET} {msg}")
def info(msg):  print(f"  {CYAN}[*]{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}[~]{RESET} {msg}")


def banner():
    print(f"""
{CYAN}{BOLD}
██████╗ ██╗  ██╗ ██████╗ ██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗╚██╗██╔╝
██████╔╝███████║██║   ██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║ ██╔██╗
██║     ██║  ██║╚██████╔╝██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝{RESET}
{MUTED}  -- Installer --{RESET}
""")


def ask(prompt, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        ans = input(f"  {prompt}{suffix}: ").strip().lower()
        if ans == "": return default
        if ans in ("y", "yes"): return True
        if ans in ("n", "no"): return False
        print(f"    {RED}Please enter y or n{RESET}")


def run(cmd, check=True):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)



def get_pip_scripts_dir():
    result = run(f'"{sys.executable}" -c "import sysconfig; print(sysconfig.get_path(\'scripts\'))"')
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return None


def get_phox_bat_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "PHOX Tools" / "bin"
    else:
        return Path.home() / ".local" / "bin"


def is_in_path(directory):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    return any(str(directory).lower() == p.lower() for p in path_dirs)


def add_to_path_windows(directory):
    directory = str(directory)
    ps = (
        f"$current = [Environment]::GetEnvironmentVariable('Path', 'User'); "
        f"if ($current -notlike '*{directory}*') {{ "
        f"  [Environment]::SetEnvironmentVariable('Path', \"$current;{directory}\", 'User'); "
        f"  Write-Output 'ADDED' "
        f"}} else {{ Write-Output 'ALREADY' }}"
    )
    result = run(f'powershell -Command "{ps}"')
    return result.returncode == 0


def add_to_path_unix(directory):
    directory = str(directory)
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    if "zsh" in shell:
        rc_file = home / ".zshrc"
    elif "fish" in shell:
        rc_file = home / ".config" / "fish" / "config.fish"
    else:
        rc_file = home / ".bashrc"

    if rc_file.exists() and directory in rc_file.read_text():
        return True, str(rc_file)

    line = f'export PATH="{directory}:$PATH"'
    with open(rc_file, "a") as f:
        f.write(f"\n# Phox Tools\n{line}\n")
    return True, str(rc_file)



def check_python():
    info(f"Python {sys.version.split()[0]} detected")
    if sys.version_info < (3, 8):
        fail("Phox requires Python 3.8 or higher")
        sys.exit(1)
    ok("Python version OK")


def install_package():
    info("Installing phox-tools package...")
    info("(running pip install -e .)")
    result = run(f'"{sys.executable}" -m pip install -e . --disable-pip-version-check')
    if result.returncode != 0:
        info("Trying without editable mode...")
        result = run(f'"{sys.executable}" -m pip install . --disable-pip-version-check')

    if result.returncode == 0:
        ok("Package installed successfully")
        return True
    else:
        fail("pip install failed!")
        if result.stderr:
            print(f"    {MUTED}{result.stderr[:300]}{RESET}")
        if result.stdout:
            print(f"    {MUTED}{result.stdout[:300]}{RESET}")
        return False


def create_phox_bat(scripts_dir):
    bat_dir = get_phox_bat_dir()
    bat_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        bat_file = bat_dir / "phox.bat"
        if scripts_dir and (scripts_dir / "phox.exe").exists():
            bat_content = f'@"{scripts_dir / "phox.exe"}" %*\n'
        else:
            bat_content = f'@python -m phox %*\n'
        bat_file.write_text(bat_content, encoding="utf-8")
        ok(f"Created {bat_file}")
        return bat_dir
    else:
        sh_file = bat_dir / "phox"
        sh_file.write_text(f'#!/bin/bash\nexec python -m phox "$@"\n', encoding="utf-8")
        os.chmod(sh_file, 0o755)
        ok(f"Created {sh_file}")
        return bat_dir


def add_to_path():
    info("Setting up phox command...")

    scripts_dir = get_pip_scripts_dir()

    bat_dir = create_phox_bat(scripts_dir)

    pip_has_phox = scripts_dir and (scripts_dir / "phox.exe").exists()
    pip_in_path = scripts_dir and is_in_path(scripts_dir)
    bat_in_path = is_in_path(bat_dir)

    print()

    if pip_has_phox and pip_in_path:
        info(f"phox.exe found at: {scripts_dir}")
        ok("Already in PATH — 'phox' command should work")
        return True

    if bat_in_path:
        info(f"phox wrapper found at: {bat_dir}")
        ok("Already in PATH — 'phox' command should work")
        return True

    dirs_to_add = []
    if scripts_dir and pip_has_phox:
        dirs_to_add.append(scripts_dir)
    dirs_to_add.append(bat_dir)

    added_any = False
    for d in dirs_to_add:
        if is_in_path(d):
            info(f"{d} already in PATH")
            continue

        info(f"Adding {d} to your PATH...")
        if sys.platform == "win32":
            if add_to_path_windows(d):
                ok(f"Added {d}")
                added_any = True
            else:
                warn(f"Could not auto-add: {d}")
                print(f"    {MUTED}Add manually via: Settings > System > About > Advanced > Environment Variables{RESET}")
        else:
            ok_added, rc_file = add_to_path_unix(d)
            if ok_added:
                ok(f"Added to {rc_file}")
                added_any = True

    if added_any:
        print()
        info("IMPORTANT: Restart your terminal for PATH changes to take effect!")
        print(f"    {MUTED}You can also run: python -m phox{RESET}")

    return True


def install_optional_deps():
    print()
    info("Optional packages that enhance Phox:")
    print(f"    {MUTED}dnspython  - Advanced DNS record types (MX, TXT, NS, SOA){RESET}")
    print()

    if ask("Install optional packages?", default=False):
        info("Installing dnspython...")
        result = run(f'"{sys.executable}" -m pip install dnspython --quiet --disable-pip-version-check')
        if result.returncode == 0:
            ok("dnspython installed")
        else:
            warn("Could not install dnspython (phox still works without it)")
    else:
        info("Skipping optional packages")


def verify_install():
    print()
    info("Verifying installation...")

    result = run("phox --version")
    if result.returncode == 0:
        ok(f"phox command works: {result.stdout.strip()}")
        return True

    result = run(f'"{sys.executable}" -m phox --version')
    if result.returncode == 0:
        ok(f"python -m phox works: {result.stdout.strip()}")
        info("If 'phox' not found, restart your terminal")
        return True

    fail("Could not verify installation")
    return False



def main():
    banner()

    check_python()

    print()
    info("Step 1: Install phox-tools")
    if not install_package():
        fail("Installation failed. Check the error above.")
        print()
        info("You can also install manually:")
        print(f"    {sys.executable} -m pip install -e .")
        print()
        sys.exit(1)

    print()
    info("Step 2: Add phox to PATH")
    if ask("Add 'phox' command to your PATH so you can run it from anywhere?", default=True):
        add_to_path()
    else:
        info("Skipping PATH setup")
        print(f"    {MUTED}You can still run: python -m phox{RESET}")

    print()
    info("Step 3: Optional packages")
    install_optional_deps()

    verify_install()

    print()
    print(f"  {GREEN}{BOLD}Installation complete!{RESET}")
    print()
    print(f"  {CYAN}Quick start:{RESET}")
    print(f"    phox                   # Show banner + help")
    print(f"    phox web               # Start web UI at http://localhost:1234")
    print(f"    phox web 3000          # Custom port")
    print(f"    phox encode base64 hi  # Quick encode")
    print(f"    phox hash \"hello\"      # Hash text")
    print(f"    phox password          # Generate passwords")
    print()
    print(f"  {MUTED}If 'phox' not found, restart your terminal or use: python -m phox{RESET}")
    print()


if __name__ == "__main__":
    main()
