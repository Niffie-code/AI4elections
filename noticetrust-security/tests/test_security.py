import io
import logging
import os
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import create_app
from nt_security.logsafe import RedactingFilter, redact
from nt_security.settings import Settings
from nt_security.storage import PrivateStorage
from nt_security.tokens import hash_token

REVIEWER_TOKEN = "reviewer-secret-token-for-tests"


def png_bytes(size=(64, 64), color=(255, 255, 255)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=str(tmp_path / "uploads"),
                    reviewer_token_hashes=(hash_token(REVIEWER_TOKEN),),
                    upload_rate_limit=1000)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def upload(client, data, name="notice.png", ctype="image/png"):
    return client.post("/api/verifications", files={"file": (name, data, ctype)})


# ---- upload controls -------------------------------------------------------
def test_valid_png_accepted(client):
    r = upload(client, png_bytes())
    assert r.status_code == 202 and len(r.json()["access_token"]) >= 40


def test_fake_extension_rejected(client):
    assert upload(client, b"<?php system($_GET['x']); ?>", "evil.png").status_code == 415


def test_wrong_type_rejected(client):
    assert upload(client, b"%PDF-1.4 fake", "x.pdf", "application/pdf").status_code == 415


def test_oversize_rejected(client):
    assert upload(client, b"\x89PNG\r\n\x1a\n" + b"0" * (12 * 1024 * 1024)).status_code == 413


def test_chunked_oversize_rejected(client):
    def gen():
        for _ in range(14):
            yield b"0" * (1024 * 1024)
    r = client.post("/api/verifications", content=gen(),
                    headers={"content-type": "multipart/form-data; boundary=x"})
    assert r.status_code == 413


def test_pixel_bomb_rejected(client):
    # tiny on disk, huge when decoded
    assert upload(client, png_bytes((6000, 6000))).status_code == 422


def test_truncated_image_rejected_cleanly(client):
    assert upload(client, png_bytes()[:40]).status_code == 422


def test_exif_and_trailing_payload_stripped():
    from nt_security.upload import validate_and_clean_image
    img = Image.new("RGB", (50, 50), "red")
    exif = Image.Exif(); exif[0x010F] = "SecretCamera"; exif[0x8825] = {1: "N"}
    b = io.BytesIO(); img.save(b, "JPEG", exif=exif)
    dirty = b.getvalue() + b"<script>alert(1)</script>"
    clean, ext = validate_and_clean_image(dirty, 25_000_000, 10_000)
    out = Image.open(io.BytesIO(clean))
    assert ext == ".jpg" and not out.getexif() and b"<script>" not in clean


# ---- access control --------------------------------------------------------
def test_job_requires_its_own_token(client):
    a, b = upload(client, png_bytes()).json(), upload(client, png_bytes((65, 65))).json()
    ok = client.get(f"/api/verifications/{a['job_id']}", headers={"Authorization": f"Bearer {a['access_token']}"})
    assert ok.status_code == 200
    cross = client.get(f"/api/verifications/{a['job_id']}", headers={"Authorization": f"Bearer {b['access_token']}"})
    none = client.get(f"/api/verifications/{a['job_id']}")
    missing = client.get("/api/verifications/" + "0" * 32, headers={"Authorization": f"Bearer {a['access_token']}"})
    assert cross.status_code == none.status_code == missing.status_code == 404
    assert cross.json() == none.json() == missing.json()           # no enumeration signal


def test_reviewer_endpoints_protected(client):
    assert client.get("/api/reviews").status_code == 401
    assert client.get("/api/reviews", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/api/reviews/" + "0" * 32 + "/decision").status_code == 401
    good = client.get("/api/reviews", headers={"Authorization": f"Bearer {REVIEWER_TOKEN}"})
    assert good.status_code == 200


def test_no_reviewer_access_when_unconfigured(tmp_path):
    s = Settings(storage_dir=str(tmp_path / "u"), reviewer_token_hashes=())
    with TestClient(create_app(s)) as c:
        assert c.get("/api/reviews", headers={"Authorization": "Bearer anything"}).status_code == 401


def test_sources_cannot_be_modified_publicly(client):
    for m in ("post", "put", "patch", "delete"):
        r = getattr(client, m)("/api/sources/abc")
        assert r.status_code in (404, 405), m


# ---- abuse limits ----------------------------------------------------------
def test_rate_limit(tmp_path):
    s = Settings(storage_dir=str(tmp_path / "u"), upload_rate_limit=3)
    with TestClient(create_app(s)) as c:
        codes = [upload(c, png_bytes()).status_code for _ in range(5)]
    assert codes[:3] == [202, 202, 202] and codes[3:] == [429, 429]


# ---- retention -------------------------------------------------------------
def test_cleanup_after_processing(client, settings):
    upload(client, png_bytes())
    time.sleep(0.3)
    assert list(PrivateStorage(settings.storage_dir).root.iterdir()) == []


def test_fallback_sweep_removes_stale_only(tmp_path):
    st = PrivateStorage(str(tmp_path / "s"))
    old, fresh = st.save("a" * 32, b"x", ".png"), st.save("b" * 32, b"x", ".png")
    os.utime(old, (time.time() - 7200, time.time() - 7200))   # 2h old
    assert st.sweep(3600) == 1 and not old.exists() and fresh.exists()


def test_storage_is_private_and_blocks_traversal(tmp_path):
    st = PrivateStorage(str(tmp_path / "p"))
    assert oct(st.root.stat().st_mode & 0o777) == "0o700"
    p = st.save("c" * 32, b"x", ".png")
    assert oct(p.stat().st_mode & 0o777) == "0o600"
    with pytest.raises(ValueError):
        st.save("../../etc/passwd", b"x", ".png")


# ---- logging & headers -----------------------------------------------------
def test_tokens_never_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    r = upload(client, png_bytes()).json()
    client.get(f"/api/verifications/{r['job_id']}", headers={"Authorization": f"Bearer {r['access_token']}"})
    assert r["access_token"] not in caplog.text


def test_redaction_filter():
    assert "abc123secret" not in redact("Authorization: Bearer abc123secret")
    assert "hunter2" not in redact("login password=hunter2 ok")
    rec = logging.LogRecord("x", logging.INFO, "", 0, "tok %s", ("A" * 50,), None)
    RedactingFilter().filter(rec)
    assert "A" * 50 not in rec.msg


def test_security_headers_and_no_docs(client):
    r = client.get("/api/sources/x")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert client.get("/docs").status_code == 404
