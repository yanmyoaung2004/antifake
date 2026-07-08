"""
Run the AntiFake server with HTTPS enabled (auto-generates cert if needed).

Usage:
    python tools/run_https.py [--port 8000] [--host 0.0.0.0]

Auto-detects cert.pem and key.pem in the backend root. If missing,
generates a self-signed cert for local development. Camera access in
the browser requires HTTPS, so this is required to test the QR scanner
on a phone.
"""
import argparse
import os
import sys
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    backend_root = os.path.join(os.path.dirname(__file__), "..")
    cert_path = os.path.join(backend_root, "cert.pem")
    key_path = os.path.join(backend_root, "key.pem")

    if not (os.path.exists(cert_path) and os.path.exists(key_path)):
        print("No cert.pem/key.pem found. Generating self-signed cert...")
        from tools.generate_cert import generate

        generate()

    url = f"https://{args.host}:{args.port}"
    print(f"\n  AntiFake server starting at {url}")
    print(f"  Open this URL on your phone (after trusting the cert).")
    print(f"  Press Ctrl+C to stop.\n")

    if not args.no_browser:
        webbrowser.open(f"https://localhost:{args.port}")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
        log_level="info",
    )


if __name__ == "__main__":
    main()
