#!/usr/bin/env python3
"""FeeDesk backup helper: PostgreSQL custom-format dump + private uploads archive.

SAFE BY DEFAULT: prints the plan and does not touch the filesystem or Docker
unless ``--execute`` is supplied.

What it does (with ``--execute``):
  1. ``pg_dump -Fc`` inside the running Compose ``db`` service.
  2. Archives the private uploads Docker volume with a throwaway Alpine container.
  3. Encrypts both artifacts with ``age`` (required for ``--execute``; local drills
     may explicitly pass ``--allow-unencrypted``).
  4. Writes a JSON manifest with SHA-256 checksums.
  5. Prunes only files matching this script's own naming pattern, older than
     ``--retention-days``. Nothing is ever restored or dropped.

It reads database credentials from the Compose service environment; it does not
read or print secrets. Run it on the Docker host as a user with Docker access.

Examples:
  python3 scripts/feedesk_backup.py                       # dry run
  python3 scripts/feedesk_backup.py --execute \\
      --backup-dir /var/backups/feedesk \\
      --metrics-textfile /var/lib/node_exporter/textfile/feedesk_backup.prom
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE_FILE = REPO_ROOT / "infra" / "compose" / "docker-compose.prod.yml"
DEFAULT_ENV_FILE = REPO_ROOT / "infra" / "compose" / ".env.production"
MANIFEST_SUFFIX = "-manifest.json"


class BackupError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up FeeDesk PostgreSQL and uploads (dry run by default).",
    )
    parser.add_argument("--execute", action="store_true", help="Actually run the backup.")
    parser.add_argument(
        "--backup-dir",
        default=os.environ.get("BACKUP_DIR"),
        help="Destination directory ($BACKUP_DIR). Required with --execute.",
    )
    parser.add_argument(
        "--compose-file",
        default=os.environ.get("COMPOSE_FILE", str(DEFAULT_COMPOSE_FILE)),
        help="Compose file to use.",
    )
    parser.add_argument(
        "--env-file",
        default=os.environ.get("COMPOSE_ENV_FILE", str(DEFAULT_ENV_FILE)),
        help="Compose env file with production placeholders.",
    )
    parser.add_argument("--project-name", default="feedesk-prod")
    parser.add_argument("--db-service", default="db")
    parser.add_argument("--db-user", default="feedesk")
    parser.add_argument("--db-name", default="feedesk")
    parser.add_argument(
        "--uploads-volume",
        default=os.environ.get("BACKUP_UPLOADS_VOLUME", "feedesk_prod_uploads"),
    )
    parser.add_argument(
        "--uploads-image",
        default="alpine:3.20",
        help="Image used for the uploads volume tar (pre-pull in production).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("BACKUP_RETENTION_DAYS", "30")),
        help="Delete matching artifacts older than this many days (minimum 1).",
    )
    parser.add_argument(
        "--age-recipient",
        default=os.environ.get("BACKUP_AGE_RECIPIENT", ""),
        help="age public key; artifacts are encrypted before retention.",
    )
    parser.add_argument(
        "--allow-unencrypted",
        action="store_true",
        help="Allow --execute without an age recipient for local drills only.",
    )
    parser.add_argument(
        "--metrics-textfile",
        default=os.environ.get("BACKUP_METRICS_TEXTFILE", ""),
        help="Optional node_exporter textfile to update on success.",
    )
    args = parser.parse_args(argv)
    if args.retention_days < 1:
        parser.error("--retention-days must be at least 1")
    if args.execute and not args.age_recipient and not args.allow_unencrypted:
        parser.error(
            "--execute requires --age-recipient (production backup encryption); "
            "use --allow-unencrypted only for local drills"
        )
    return args


def compose_cmd(args: argparse.Namespace) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        args.project_name,
        "--env-file",
        args.env_file,
        "-f",
        args.compose_file,
    ]


def run(cmd: list[str], *, execute: bool, stdin=None, stdout=None) -> int:
    printable = shlex.join(str(part) for part in cmd)
    if not execute:
        print(f"[dry-run] {printable}")
        return 0
    if shutil.which(cmd[0]) is None:
        raise BackupError(f"required executable not found: {cmd[0]}")
    print(f"[run] {printable}")
    completed = subprocess.run(cmd, stdin=stdin, stdout=stdout)
    if completed.returncode != 0:
        raise BackupError(f"command failed with exit {completed.returncode}: {printable}")
    return completed.returncode


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_partial(path: Path, execute: bool) -> None:
    if execute and path.exists():
        path.unlink()


def encrypt(path: Path, recipient: str, execute: bool) -> Path:
    target = path.with_suffix(path.suffix + ".age")
    if execute and shutil.which("age") is None:
        raise BackupError("--age-recipient was set but the 'age' executable is missing")
    run(["age", "--recipient", recipient, "--output", str(target), str(path)], execute=execute)
    if execute:
        path.unlink()
    return target


def prune(backup_dir: Path, retention_days: int, execute: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    patterns = ("*.dump", "*.dump.age", "*.tar.gz", "*.tar.gz.age", "*" + MANIFEST_SUFFIX)
    candidates: set[Path] = set()
    if backup_dir.exists():
        for pattern in patterns:
            candidates.update(backup_dir.glob("feedesk-" + pattern))
    for path in sorted(candidates):
        if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            print(f"[prune] {path}")
            if execute:
                path.unlink()
    if not candidates:
        print("[prune] no matching artifacts")


def write_metrics(path: str, dump_size: int, execute: bool) -> None:
    if not path:
        return
    target = Path(path)
    if not execute:
        print(f"[dry-run] write metrics to {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# TYPE feedesk_backup_last_success_timestamp_seconds gauge\n"
        f"feedesk_backup_last_success_timestamp_seconds {int(time.time())}\n"
        "# TYPE feedesk_backup_last_dump_size_bytes gauge\n"
        f"feedesk_backup_last_dump_size_bytes {dump_size}\n"
    )
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(body, encoding="utf-8")
    temp.replace(target)


def main(argv: list[str] | None = None) -> int:
    # Backups may be plaintext when encryption is not configured; keep them
    # owner-only regardless.
    os.umask(0o077)
    args = parse_args(argv)
    execute = args.execute
    if execute and not args.backup_dir:
        raise BackupError("--backup-dir or BACKUP_DIR is required with --execute")
    started = time.monotonic()
    backup_dir = Path(args.backup_dir or REPO_ROOT / "feedesk-backups").expanduser().resolve()
    compose_file = Path(args.compose_file).expanduser().resolve()
    env_file = Path(args.env_file).expanduser().resolve()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"feedesk-{timestamp}"
    dump_path = backup_dir / f"{prefix}-db.dump"
    uploads_path = backup_dir / f"{prefix}-uploads.tar.gz"
    manifest_path = backup_dir / f"{prefix}{MANIFEST_SUFFIX}"

    print(f"[plan] mode          {'EXECUTE' if execute else 'DRY RUN'}")
    print(f"[plan] backup dir    {backup_dir}")
    print(f"[plan] compose file  {compose_file}")
    print(f"[plan] env file      {env_file}")
    print(f"[plan] database      {args.db_name} (service {args.db_service})")
    print(f"[plan] uploads       {args.uploads_volume}")
    print(f"[plan] retention     {args.retention_days} days")
    print(f"[plan] encryption    {'age recipient configured' if args.age_recipient else 'NONE (required in production)'}")

    if execute:
        if not compose_file.is_file():
            raise BackupError(f"compose file not found: {compose_file}")
        if not env_file.is_file():
            raise BackupError(f"env file not found: {env_file}")
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    else:
        print(f"[dry-run] would create {backup_dir}")

    base = compose_cmd(args)

    # 1. Database dump. Credentials come from the container environment, not argv.
    # Do not create the output file in dry-run mode.
    handle = dump_path.open("wb") if execute else None
    try:
        run(
            base
            + [
                "exec",
                "-T",
                args.db_service,
                "pg_dump",
                "-U",
                args.db_user,
                "-d",
                args.db_name,
                "-Fc",
                "--no-owner",
                "--no-privileges",
            ],
            execute=execute,
            stdout=handle,
        )
    except Exception:
        remove_partial(dump_path, execute)
        raise
    finally:
        if handle is not None:
            handle.close()

    # 2. Private uploads volume archive.
    try:
        run(
            [
                "docker",
                "volume",
                "inspect",
                args.uploads_volume,
            ],
            execute=execute,
            stdout=subprocess.DEVNULL,
        )
        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{args.uploads_volume}:/data:ro",
                "-v",
                f"{backup_dir}:/backup",
                args.uploads_image,
                "tar",
                "-czf",
                f"/backup/{uploads_path.name}",
                "-C",
                "/data",
                ".",
            ],
            execute=execute,
        )
    except Exception:
        remove_partial(uploads_path, execute)
        raise

    final_dump = dump_path
    final_uploads = uploads_path
    if args.age_recipient:
        final_dump = encrypt(dump_path, args.age_recipient, execute)
        final_uploads = encrypt(uploads_path, args.age_recipient, execute)

    # 3. Manifest with checksums (written last, so a partial backup has none).
    files = []
    if execute:
        for artifact in (final_dump, final_uploads):
            stat = artifact.stat()
            files.append(
                {
                    "name": artifact.name,
                    "bytes": stat.st_size,
                    "sha256": sha256_file(artifact),
                }
            )
    manifest = {
        "app": "FeeDesk",
        "kind": "database+uploads",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": args.db_name,
        "uploads_volume": args.uploads_volume,
        "encrypted": bool(args.age_recipient),
        "retention_days": args.retention_days,
        "rpo_note": "Proposed RPO <= 24h when run daily; not verified in production.",
        "files": files,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    if execute:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"[done] manifest {manifest_path}")
    else:
        print(f"[dry-run] would write manifest {manifest_path}")

    prune(backup_dir, args.retention_days, execute)
    write_metrics(args.metrics_textfile, manifest["files"][0]["bytes"] if execute else 0, execute)
    print("[done] backup complete" if execute else "[dry-run] no changes made")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BackupError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
