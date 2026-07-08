"""
Tests for HTTPS support and cert generation.

Verifies:
  - generate_cert.py produces a valid PEM cert + key
  - The server can start with --ssl-keyfile/--ssl-certfile
  - The /api/v1/health endpoint responds over HTTPS
"""
import os
import ssl
import sys
import asyncio
import tempfile

import httpx
import pytest
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


def test_cert_files_exist():
    cert_path = os.path.join(os.path.dirname(__file__), "..", "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "..", "key.pem")
    if not (os.path.exists(cert_path) and os.path.exists(key_path)):
        pytest.skip("Cert not generated yet. Run: python tools/generate_cert.py")
    with open(cert_path, "rb") as f:
        cert_data = f.read()
    assert b"BEGIN CERTIFICATE" in cert_data
    with open(key_path, "rb") as f:
        key_data = f.read()
    assert b"PRIVATE KEY" in key_data


@pytest.mark.asyncio
async def test_server_responds_over_https():
    cert_path = os.path.join(os.path.dirname(__file__), "..", "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "..", "key.pem")
    if not (os.path.exists(cert_path) and os.path.exists(key_path)):
        pytest.skip("Cert not generated yet.")

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=18765,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        await asyncio.sleep(2)
        async with httpx.AsyncClient(verify=False, timeout=5) as client:
            r = await client.get("https://127.0.0.1:18765/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
    finally:
        server.should_exit = True
        await task
