from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import settings
from app.models import SourceFile, User
from app.security import hash_password

from .conftest import SessionLocal, login


def _add_source_file(storage_key: str, *, filename: str = "statement.csv") -> str:
    with SessionLocal() as db:
        row = SourceFile(
            storage_key=storage_key,
            original_filename=filename,
            content_type="text/csv",
            file_size=1,
            sha256_hash="0" * 64,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def test_file_download_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/files/does-not-exist")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_file_download_blocks_path_traversal(
    admin_client: tuple[TestClient, str], tmp_path: Path, monkeypatch
) -> None:
    client, _ = admin_client
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    outside = tmp_path.parent / "outside.csv"
    outside.write_bytes(b"private\n")
    file_id = _add_source_file("../outside.csv")

    response = client.get(f"/api/v1/files/{file_id}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PATH"


def test_file_download_serves_file_inside_upload_root(
    admin_client: tuple[TestClient, str], tmp_path: Path, monkeypatch
) -> None:
    client, _ = admin_client
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    target = tmp_path / "statements" / "statement.csv"
    target.parent.mkdir()
    target.write_bytes(b"guardian,amount\n")
    file_id = _add_source_file("statements/statement.csv")

    response = client.get(f"/api/v1/files/{file_id}")

    assert response.status_code == 200
    assert response.content == b"guardian,amount\n"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_file_download_requires_dedicated_permission(
    client: TestClient,
    staff_client: tuple[TestClient, str],
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app import security

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    target = tmp_path / "statements" / "permission.csv"
    target.parent.mkdir()
    target.write_bytes(b"guardian,amount\n")
    file_id = _add_source_file("statements/permission.csv")

    staff, _ = staff_client
    assert staff.get(f"/api/v1/files/{file_id}").status_code == 200

    # A role with imports.view but without files.download must be denied.  This
    # proves the file route no longer piggybacks on the imports permission.
    monkeypatch.setitem(
        security.ROLE_PERMISSIONS, "viewer", {"imports.view"}
    )
    username = f"viewer_file_{uuid4().hex[:10]}"
    with SessionLocal() as db:
        db.add(
            User(
                username=username,
                password_hash=hash_password("ViewerFile!2026"),
                role="viewer",
                is_active=True,
                must_change_password=False,
            )
        )
        db.commit()

    login(client, username, "ViewerFile!2026")
    denied = client.get(f"/api/v1/files/{file_id}")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"
