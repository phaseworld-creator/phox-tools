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
{RED}{BOLD}
██████╗ ██╗  ██╗ ██████╗ ██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗╚██╗██╔╝
██████╔╝███████║██║   ██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║ ██╔██╗
██║     ██║  ██║╚██████╔╝██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝{RESET}
{MUTED}  ── Uninstaller ──{RESET}
""")


def ask(prompt, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        ans = input(f"  {prompt}{suffix}: ").strip().lower()
        if ans == "": return default
        if ans in ("y", "yes"): return True
        if ans in ("n", "no"): return False
        print(f"    {RED}Please enter y or n{RESET}")


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)



def get_user_scripts_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "~")) / "Python" / "Scripts"
    else:
        return Path.home() / ".local" / "bin"


def get_site_packages_scripts():
    result = run(f'"{sys.executable}" -c "import sysconfig; print(sysconfig.get_path(\'scripts\'))"')
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None


def remove_from_path_windows(directory):
    directory = str(directory)
    ps_cmd = (
        f"$p = [Environment]::GetEnvironmentVariable('Path', 'User'); "
        f"$dirs = $p -split ';' | Where-Object {{ $_ -ne '{directory}' }}; "
        f"[Environment]::SetEnvironmentVariable('Path', ($dirs -join ';'), 'User')"
    )
    result = run(f'powershell -Command "{ps_cmd}"')
    return result.returncode == 0


def remove_from_path_unix(directory):
    directory = str(directory)
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    if "zsh" in shell:
        rc_file = home / ".zshrc"
    elif "fish" in shell:
        rc_file = home / ".config" / "fish" / "config.fish"
    else:
        rc_file = home / ".bashrc"

    if not rc_file.exists():
        return False, str(rc_file)

    content = rc_file.read_text(encoding="utf-8", errors="replace")

    lines = content.split("\n")
    new_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.strip() == "# Phox Tools":
            skip_next = True
            continue
        if directory in line and "PATH" in line:
            continue
        new_lines.append(line)

    new_content = "\n".join(new_lines)
    if new_content != content:
        rc_file.write_text(new_content, encoding="utf-8")
        return True, str(rc_file)
    return False, str(rc_file)



def check_phox_installed():
    result = run("phox --version")
    if result.returncode == 0:
        return True, result.stdout.strip()

    result = run(f'"{sys.executable}" -m phox --version')
    if result.returncode == 0:
        return True, result.stdout.strip()

    return False, None


def uninstall_package():
    info("Uninstalling phox-tools package...")

    result = run(f'"{sys.executable}" -m pip uninstall phox-tools -y --quiet')
    if result.returncode == 0:
        ok("Package uninstalled")
        return True

    result = run(f'"{sys.executable}" -m pip uninstall phox -y --quiet')
    if result.returncode == 0:
        ok("Package uninstalled")
        return True

    fail(f"pip uninstall failed: {result.stderr[:200]}")
    return False


def remove_shortcut():
    if sys.platform != "win32":
        return

    scripts_dir = get_site_packages_scripts()
    bat_file = scripts_dir / "p.bat"

    if bat_file.exists():
        info(f"Removing shortcut: {bat_file}")
        bat_file.unlink()
        ok("Shortcut removed")
    else:
        info("No 'p' shortcut found")


def remove_from_path():
    scripts_dir = get_site_packages_scripts()

    if scripts_dir and scripts_dir.exists():
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        in_path = str(scripts_dir) in path_dirs or str(scripts_dir).lower() in [p.lower() for p in path_dirs]

        if in_path:
            info(f"Removing from PATH: {scripts_dir}")

            if sys.platform == "win32":
                success = remove_from_path_windows(scripts_dir)
            else:
                success, _ = remove_from_path_unix(scripts_dir)

            if success:
                ok("Removed from PATH (restart terminal to apply)")
            else:
                warn("Could not auto-remove from PATH")
        else:
            info("Scripts directory not in PATH (nothing to remove)")

    user_dir = get_user_scripts_dir()
    if user_dir.exists():
        try:
            remaining = list(user_dir.iterdir())
            if not remaining:
                info(f"Removing empty directory: {user_dir}")
                user_dir.rmdir()
                ok("Empty scripts directory removed")
        except Exception:
            pass


def remove_config():
    phox_dir = Path.home() / ".phox"

    if not phox_dir.exists():
        info("No config directory found (~/.phox)")
        return

    contents = list(phox_dir.iterdir())
    size_info = ""
    total_files = 0
    for item in contents:
        if item.is_dir():
            total_files += len(list(item.rglob("*")))
        else:
            total_files += 1

    print()
    info(f"Config directory: {phox_dir}")
    info(f"Contains: {total_files} files across {len(contents)} items")
    print()
    print(f"    {MUTED}This includes:{RESET}")
    print(f"    {MUTED}  - Custom commands (~/.phox/commands/){RESET}")
    print(f"    {MUTED}  - Themes (~/.phox/themes/){RESET}")
    print(f"    {MUTED}  - Config (~/.phox/config.json){RESET}")

    if ask("\nDelete config directory and all custom commands?", default=False):
        shutil.rmtree(phox_dir)
        ok("Config directory removed")
    else:
        info("Keeping config directory")


def verify_uninstall():
    info("Verifying uninstallation...")

    result = run("phox --version")
    if result.returncode == 0:
        warn("phox command still available (restart terminal to apply)")
        return False

    result = run(f'"{sys.executable}" -m phox --version')
    if result.returncode == 0:
        warn("phox module still importable (was installed in development mode)")
        info("If using 'pip install -e .', the package directory still exists")
        info("You can delete the project folder manually")
        return False

    ok("phox is no longer accessible")
    return True



def main():
    banner()

    installed, version = check_phox_installed()
    if not installed:
        warn("phox-tools does not appear to be installed")
        if not ask("Continue anyway?", default=False):
            info("Nothing to uninstall")
            sys.exit(0)
    else:
        info(f"Found: {version}")

    print()
    warn("This will remove phox-tools from your system")
    if not ask("Are you sure you want to uninstall?", default=False):
        info("Uninstall cancelled")
        sys.exit(0)

    print()
    info("Step 1: Uninstall package")
    uninstall_package()

    print()
    info("Step 2: Clean up PATH")
    remove_from_path()

    if sys.platform == "win32":
        print()
        info("Step 3: Remove shortcuts")
        remove_shortcut()

    print()
    info("Step 4: Config directory")
    remove_config()

    print()
    verify_uninstall()

    print()
    print(f"  {GREEN}{BOLD}Uninstallation complete!{RESET}")
    print()
    print(f"  {CYAN}Restart your terminal for changes to take effect{RESET}")
    print(f"  {MUTED}To reinstall: python install.py{RESET}")
    print()


if __name__ == "__main__":
    main()
