# PHOX Tools

A Swiss Army Knife for Hackers and Developers.
##
See all the [commands](https://github.com/phaseworld-creator/phox-tools/blob/main/HELP.md)
## Install


```bash
git clone https://github.com/phaseworld-creator/phox-tools.git
cd phox-tools
```
```bash
python install.py
```

Or manually:

```bash
pip install -e .
```

## Usage

```bash
phox                    # Show banner
phox help               # Full command list with examples
phox help <command>     # Detailed help for a specific command
```

## Commands (22+9 web)

### Encoding
| Command | Description |
|---------|-------------|
| `phox encode <base64\|hex\|url> <text>` | Encode text |
| `phox decode <base64\|hex\|url> <text>` | Decode text |
| `phox hash <text> [-a ALGO]` | Hash text |
| `phox hash-all <text>` | Hash with all algorithms |
| `phox hash-file <file> [-a ALGO] [--all] [-r]` | Hash files |
| `phox password [-l LEN] [-n COUNT]` | Generate passwords |
| `phox rand [-t TYPE] [-n COUNT]` | Random data generator |

### Recon
| Command | Description |
|---------|-------------|
| `phox ip-lookup [IP]` | IP geolocation (34 fields) |
| `phox dns <domain> [-t TYPE]` | DNS lookup |
| `phox whois <domain>` | WHOIS/RDAP lookup |
| `phox username <name> [-p PLATFORMS]` | Username check (42+ platforms) |
| `phox portscan <host> [-p PORTS]` | Port scanner |
| `phox subdomain <domain>` | Subdomain enumeration |

### Web
| Command | Description |
|---------|-------------|
| `phox web [port]` | Start web UI (default: localhost:1234) |
| `phox search <query>` | DuckDuckGo search |
| `phox api <url> [-X METHOD]` | HTTP API client |
| `phox qr <text> [--format svg\|txt\|png]` | QR code generator |
| `phox cloner <url> [-d DEPTH]` | Website cloner |

### Security
| Command | Description |
|---------|-------------|
| `phox obfuscate <file.py> [-l LAYERS]` | Python obfuscator |

### Utilities
| Command | Description |
|---------|-------------|
| `phox webhook <send\|discord\|list\|fire\|history>` | Webhook manager |
| `phox theme <list\|set\|preset\|create>` | Theme customization |
| `phox custom <new\|list\|run\|edit\|delete>` | Custom commands |
| `phox config [list\|get\|set\|reset]` | Configuration manager |
| `phox colors [--test]` | Color palette display |
| `phox banner` | ASCII art banner |

### Web-Only Tools (no CLI)
| Tool | Description |
|------|-------------|
| UUID Generator | Generate v1/v4/v5 UUIDs |
| Timestamp Converter | Unix, ISO, human date conversion |
| Binary Converter | Text to/from binary |
| Morse Code | Encode/decode Morse code |
| Color Converter | HEX/RGB/HSL/Decimal conversion |
| Lorem Ipsum | Generate placeholder text |
| Text Diff | Compare two texts side by side |
| Hash Lookup | Look up hashes in common databases |
| Module Visibility | Toggle which tools appear in the UI |

## Web UI

Start the web dashboard:

```bash
phox web           # http://localhost:1234
phox web 3000      # Custom port
```

Features:
- 18+ tool pages with modern dark UI
- Dashboard with tool cards
- Copy-to-clipboard on all outputs
- Toast notifications
- Responsive design
- Settings manager

## Config

```bash
phox config                # Open config in editor
phox config list           # Show all settings
phox config get web.port   # Get a setting
phox config set web.port 8080  # Change a setting
phox config reset          # Reset to defaults
```

## Install / Update / Uninstall

```bash
python install.py          # Install phox
python update.py           # Update phox
python uninstall.py        # Remove phox
```

## Custom Commands [WIP]

```bash
phox custom new my-tool -d "My custom tool"
phox custom list
phox custom run my-tool
```

Custom commands are stored in `~/.phox/commands/` as Python files.

## License

MIT [Custome]
