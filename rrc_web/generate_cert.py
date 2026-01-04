#!/usr/bin/env python3
"""Generate self-signed SSL certificates for RRC Web Client."""

from __future__ import annotations

import argparse
import datetime
import logging
import secrets
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)

DEFAULT_CERT_DIR = Path.home() / ".rrc-web"
DEFAULT_VALIDITY_DAYS = 365


def generate_self_signed_cert(
    cert_path: Path,
    key_path: Path,
    hostname: str = "localhost",
    validity_days: int = DEFAULT_VALIDITY_DAYS,
) -> bool:
    """Generate a self-signed SSL certificate and private key.

    Args:
        cert_path: Path where certificate will be saved
        key_path: Path where private key will be saved
        hostname: Hostname to include in certificate (default: localhost)
        validity_days: Number of days the certificate is valid

    Returns:
        True if generation was successful, False otherwise
    """
    try:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "RRC Web Client"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=validity_days)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(hostname),
                        x509.DNSName("localhost"),
                        x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        try:
            key_path.chmod(0o600)
            cert_path.chmod(0o644)
        except Exception:  # nosec B110
            # Permission errors on some filesystems are non-fatal
            pass

        logger.info("Generated self-signed certificate at %s", cert_path)
        logger.info("Generated private key at %s", key_path)
        return True

    except Exception as e:
        logger.exception("Failed to generate certificate: %s", e)
        return False


def generate_auth_token() -> str:
    """Generate a secure random authentication token.

    Returns:
        URL-safe random token string
    """
    return secrets.token_urlsafe(32)


def main() -> int:
    """Main entry point for certificate generation utility."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Generate self-signed SSL certificates for RRC Web Client"
    )
    parser.add_argument(
        "--cert",
        type=Path,
        default=DEFAULT_CERT_DIR / "cert.pem",
        help="Path to save certificate (default: ~/.rrc-web/cert.pem)",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=DEFAULT_CERT_DIR / "key.pem",
        help="Path to save private key (default: ~/.rrc-web/key.pem)",
    )
    parser.add_argument(
        "--hostname",
        default="localhost",
        help="Hostname for certificate (default: localhost)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_VALIDITY_DAYS,
        help=f"Certificate validity in days (default: {DEFAULT_VALIDITY_DAYS})",
    )
    parser.add_argument(
        "--generate-token",
        action="store_true",
        help="Generate an authentication token",
    )

    args = parser.parse_args()

    if args.generate_token:
        token = generate_auth_token()
        print("\nGenerated authentication token:")
        print(f"  {token}")
        print("\nAdd this to your config.json:")
        print('  "enable_auth": true,')
        print(f'  "auth_token": "{token}",')
        print()
        return 0

    success = generate_self_signed_cert(
        cert_path=args.cert,
        key_path=args.key,
        hostname=args.hostname,
        validity_days=args.days,
    )

    if success:
        print("\n✓ Successfully generated SSL certificate and private key")
        print(f"\nCertificate: {args.cert}")
        print(f"Private key: {args.key}")
        print(f"Valid for:   {args.days} days")
        print(f"Hostname:    {args.hostname}")
        print("\nTo enable SSL, update your config.json:")
        print('  "enable_ssl": true,')
        print(f'  "ssl_cert_path": "{args.cert}",')
        print(f'  "ssl_key_path": "{args.key}",')
        print()
        print("⚠ Note: This is a self-signed certificate. Your browser will show")
        print("  a security warning. This is expected and safe for local use.")
        print()
        return 0
    else:
        print("\n✗ Failed to generate certificate. Check logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
