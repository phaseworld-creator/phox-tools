```██████╗ ██╗  ██╗ ██████╗ ██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗╚██╗██╔╝
██████╔╝███████║██║   ██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║ ██╔██╗
██║     ██║  ██║╚██████╔╝██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝```
  ── Swiss Army Knife for Hackers ──

  ────────────────────────────────────────────────────────────
    ENCODING
  ────────────────────────────────────────────────────────────
    encode          Encode text into various formats
    decode          Decode encoded text back to original
    hash            Hash text with cryptographic algorithms
    hash-all        Hash text with ALL algorithms at once
    hash-file       Hash a file or directory
    password        Generate cryptographically secure random passwords
    rand            Generate random data (strings, numbers, UUIDs, IPs, etc.)

  ────────────────────────────────────────────────────────────
    WEB
  ────────────────────────────────────────────────────────────
    cloner          Clone an entire website with depth control and concurrency
    search          Search the web via DuckDuckGo
    api             Make HTTP API requests
    qr              Generate QR codes from text or URLs

  ────────────────────────────────────────────────────────────
    RECON
  ────────────────────────────────────────────────────────────
    subdomain       Enumerate subdomains via DNS and HTTP probing
    portscan        Scan ports on a target host
    ip-lookup       Full IP geolocation with security flags
    dns             Resolve DNS records for a domain
    whois           WHOIS/RDAP domain registration lookup
    username        Check username availability across 40+ platforms

  ────────────────────────────────────────────────────────────
    SECURITY
  ────────────────────────────────────────────────────────────
    obfuscate       Obfuscate Python code with string encryption and junk code injection

  ────────────────────────────────────────────────────────────
    UTILITIES
  ────────────────────────────────────────────────────────────
    colors          Display terminal color palette and test color support
    webhook         Send and manage webhooks (including Discord)
    theme           Customize Phox terminal appearance
    custom          Create and manage your own custom commands
    web             Start the web UI in your browser
    banner          Display the PHOX ASCII art banner

  ────────────────────────────────────────────────────────────
    TIPS
  ────────────────────────────────────────────────────────────
    Combine encode + hash:
      $ phox hash "$(phox encode base64 "secret")"
    Quick recon sweep:
      $ phox ip-lookup && phox dns target.com
    Check all username handles:
      $ phox username myname -p github twitter
    Generate + save QR:
      $ phox qr "https://example.com" -o link.svg
    Full port scan:
      $ phox portscan target.com -p 1-65535
    Batch hash file:
      $ phox hash-file ./project --all -r

  ────────────────────────────────────────────────────────────
  v1.0.0  |  Zero dependencies  |  Pure Python
  Run  phox help <command>  for detailed usage and examples
