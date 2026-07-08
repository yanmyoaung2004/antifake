"""
Generates a self-signed SSL certificate for local development.

Required for browser camera access (getUserMedia requires HTTPS, except
on localhost). For production, use a real CA-signed certificate (e.g.
Let's Encrypt via certbot).

Usage:
    python tools/generate_cert.py
Outputs:
    cert.pem  - self-signed certificate
    key.pem   - private key
"""
import datetime
import ipaddress
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def generate():
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("Installing 'cryptography' for cert generation...")
        os.system(f"{sys.executable} -m pip install cryptography")
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

    out_dir = os.path.join(os.path.dirname(__file__), "..")
    cert_path = os.path.join(out_dir, "cert.pem")
    key_path = os.path.join(out_dir, "key.pem")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "antifake.local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AntiFake"),
        ]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("antifake.local"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    print(f"  Wrote {cert_path}")
    print(f"  Wrote {key_path}")
    print()
    print("  Trust this cert on your phone to enable camera access:")
    print("    iOS: Settings > General > About > Certificate Trust Settings")
    print("    Android: Chrome > Settings > Site settings > insecure/secure")
    print()
    print("  Start the server with HTTPS:")
    print("    .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload")


if __name__ == "__main__":
    generate()
