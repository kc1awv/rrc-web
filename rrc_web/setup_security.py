#!/usr/bin/env python3
"""Quick setup script for RRC Web security features."""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

from rrc_web.config import get_config_path
from rrc_web.generate_cert import generate_self_signed_cert


def main() -> int:
    """Interactive setup for security features."""
    print("=" * 32)
    print("RRC Web Security Setup")
    print("=" * 32)
    print()

    config_path = Path(get_config_path())

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        print(f"Found existing config at {config_path}")
    else:
        print(f"[WARN] Config file not found at {config_path}")
        print("  Run 'rrc-web' once to generate a default config, then run this script.")
        return 1

    print()
    print("This script will help you set up:")
    print("  1. Authentication (password protection)")
    print("  2. SSL/TLS (HTTPS encryption)")
    print()

    print("-" * 32)
    print("Authentication Setup")
    print("-" * 32)
    enable_auth = input("Enable authentication? [y/N]: ").strip().lower() == "y"

    if enable_auth:
        print("\nGenerating secure authentication token...")
        auth_token = secrets.token_urlsafe(32)
        config["enable_auth"] = True
        config["auth_token"] = auth_token
        print(f"Generated token: {auth_token}")
        print("\nIMPORTANT: Save this token securely! You'll need it to log in.")
        print("  Consider storing it in a password manager.")
    else:
        config["enable_auth"] = False
        config["auth_token"] = ""  # nosec B105

    print()

    print("-" * 32)
    print("SSL/TLS Setup")
    print("-" * 32)
    enable_ssl = input("Enable SSL/TLS (HTTPS)? [y/N]: ").strip().lower() == "y"

    if enable_ssl:
        hostname = input("\nEnter hostname [localhost]: ").strip() or "localhost"
        days_input = input("Certificate validity (days) [365]: ").strip()
        try:
            days = int(days_input) if days_input else 365
        except ValueError:
            days = 365

        cert_dir = config_path.parent
        cert_path = cert_dir / "cert.pem"
        key_path = cert_dir / "key.pem"

        print(f"\nGenerating self-signed certificate for '{hostname}'...")
        if generate_self_signed_cert(cert_path, key_path, hostname, days):
            config["enable_ssl"] = True
            config["ssl_cert_path"] = str(cert_path)
            config["ssl_key_path"] = str(key_path)
            print(f"Certificate saved to {cert_path}")
            print(f"Private key saved to {key_path}")
        else:
            print("✗ Failed to generate certificate")
            enable_ssl = False
    else:
        config["enable_ssl"] = False

    if enable_ssl:
        port = config.get("server_port", 8080)
        host = config.get("server_host", "localhost")
        config["allowed_origins"] = [f"https://{host}:{port}", f"https://localhost:{port}"]

    print()
    print("-" * 32)
    print("Saving Configuration")
    print("-" * 32)

    if config_path.exists():
        backup_path = config_path.with_suffix(".json.backup")
        import shutil

        shutil.copy2(config_path, backup_path)
        print(f"Backed up existing config to {backup_path}")

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"Saved updated config to {config_path}")

    print()
    print("=" * 32)
    print("Setup Complete!")
    print("=" * 32)
    print()

    if enable_auth:
        print("Authentication: ENABLED")
        print(f"   Token: {config['auth_token']}")
        print()

    if enable_ssl:
        port = config.get("server_port", 8080)
        print("SSL/TLS: ENABLED")
        print(f"   Access your app at: https://localhost:{port}")
        print("   [IMPORTANT] Your browser will show a security warning for the self-signed")
        print("     certificate. This is expected and safe for local use.")
        print()
    elif enable_auth:
        port = config.get("server_port", 8080)
        print("SSL/TLS: DISABLED")
        print("  Consider enabling SSL/TLS to encrypt your authentication token")
        print("  in transit. Without SSL, the token is sent in plain text.")
        print(f"   Current access: http://localhost:{port}")
        print()

    if not enable_auth and not enable_ssl:
        print("No security features enabled.")
        print("  Your web interface is accessible without authentication.")
        print()

    print("Next steps:")
    print("  1. Start RRC Web: rrc-web")
    if enable_auth:
        print("  2. Log in with your authentication token")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
