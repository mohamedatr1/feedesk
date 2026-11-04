#!/usr/bin/env python3
"""FeeDesk restore verification helper (scratch only, dry run by default).

This script never restores into the production database or uploads volume.
It refuses any target that does not match ``feedesk_restore_...``.

With ``--execute`` it:
  1. Creates a scratch PostgreSQL database in the Compose ``db`` service.
  2. Restores the custom-format dump into that scratch database.
  3. Prints row-count checks (users, audit_events, school_settings).
  4. Verifies the uploads archive (tar member count, path traversal check) and
     optionally extracts it into a scratch Docker volume named ``feedesk_restore_*``.

Cleanup is deliberately manual so the operator can inspect the scratch data.

Examples:
  python3 scripts/feedesk_restore.py --dump /var/backups/feedesk/feedesk-...-db.dump
  python3 scripts/feedesk_restore.py --dump ... --execute
  python3 scripts/feedesk_restore.py --dump ... --uploads-archive ... --execute
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE_FILE = REPO_ROOT / "infra" / "compose" / "docker-compose.prod.yml"
DEFAULT_ENV_FILE = REPO_ROOT / "infra" / "compose" / ".env.production"
SCRATCH_DB_RE = re.compile(r"^feedesk_restore_[a-z0-9_]+$")
SCRATCH_VOLUME_RE = SCRATCH_DB_RE
CHECK_QUERIES = (
    ("users", "SELECT count(*) FROM users;"),
    ("audit_events", "SELECT count(*) FROM audit_events;"),
    ("school_settings", "SELECT count(*) FROM school_settings;"),
)


class RestoreError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(
        description="Restore a FeeDesk dump into a scratch database (dry run by default).",
    )
    parser.add_argument("--dump", required=True, help="PostgreSQL custom-format dump.")
    parser.add_argument(
        "--uploads-archive",
        default="",
        help="Optional uploads .tar.gz from scripts/feedesk_backup.py.",
    )
    parser.add_argument(
        "--target-db",
        default=f"feedesk_restore_verify_{stamp}",
        help="Scratch database name; must start with feedesk_restore_.",
    )
    parser.add_argument(
        "--uploads-target-volume",
        default="",
        help="Scratch Docker volume; must start with feedesk_restore_.",
    )
    parser.add_argument(
        "--drop-existing-scratch",
        action="store_true",
        help="Drop the scratch database first if it exists (scratch names only).",
    )
    parser.add_argument("--execute", action="store_true", help="Actually perform the restore.")
    parser.add_argument(
        "--compose-file",
        default=os.environ.get("COMPOSE_FILE", str(DEFAULT_COMPOSE_FILE)),
    )
    parser.add_argument(
        "--env-file",
        default=os.environ.get("COMPOSE_ENV_FILE", str(DEFAULT_ENV_FILE)),
    )
    parser.add_argument("--project-name", default="feedesk-prod")
    parser.add_argument("--db-service", default="db")
    parser.add_argument("--db-user", default="feedesk")
    parser.add_argument("--uploads-image", default="alpine:3.20")
    args = parser.parse_args(argv)

    if not SCRATCH_DB_RE.match(args.target_db):
        parser.error("--target-db must match ^feedesk_restore_[a-z0-9_]+$ (production is refused)")
    if args.uploads_target_volume and not SCRATCH_VOLUME_RE.match(args.uploads_target_volume):
        parser.error(
            "--uploads-target-volume must match ^feedesk_restore_[a-z0-9_]+$ (production is refused)"
        )
    if args.drop_existing_scratch and not SCRATCH_DB_RE.match(args.target_db):
        parser.error("refusing to drop a non-scratch database")
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
        raise RestoreError(f"required executable not found: {cmd[0]}")
    print(f"[run] {printable}")
    completed = subprocess.run(cmd, stdin=stdin, stdout=stdout)
    if completed.returncode != 0:
        raise RestoreError(f"command failed with exit {completed.returncode}: {printable}")
    return completed.returncode


def inspect_uploads_archive(path: Path, execute: bool) -> int:
    if not execute:
        print(f"[dry-run] would inspect tar archive {path}")
        return 0
    if not path.is_file():
        raise RestoreError(f"uploads archive not found: {path}")
    count = 0
    total_bytes = 0
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = member.name.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                raise RestoreError(f"unsafe tar member refused: {member.name}")
            if member.issym() or member.islnk():
                target = member.linkname.replace("\\", "/")
                if target.startswith("/") or ".." in Path(target).parts:
                    raise RestoreError(f"unsafe tar link refused: {member.name} -> {member.linkname}")
            if member.isdev():
                raise RestoreError(f"device tar member refused: {member.name}")
            if member.isfile():
                count += 1
                total_bytes += member.size
    print(f"[check] uploads files={count} bytes={total_bytes}")
    return count


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    execute = args.execute
    dump = Path(args.dump).expanduser().resolve()
    uploads = Path(args.uploads_archive).expanduser().resolve() if args.uploads_archive else None
    compose_file = Path(args.compose_file).expanduser().resolve()
    env_file = Path(args.env_file).expanduser().resolve()

    print(f"[plan] mode          {'EXECUTE (scratch only)' if execute else 'DRY RUN'}")
    print(f"[plan] dump          {dump}")
    print(f"[plan] uploads       {uploads or '(not supplied)'}")
    print(f"[plan] scratch db    {args.target_db}")
    print(f"[plan] scratch volume {args.uploads_target_volume or '(not supplied)'}")
    print("[plan] production database and uploads volume are never targeted")

    if execute:
        if not dump.is_file():
            raise RestoreError(f"dump not found: {dump}")
        if not compose_file.is_file():
            raise RestoreError(f"compose file not found: {compose_file}")
        if not env_file.is_file():
            raise RestoreError(f"env file not found: {env_file}")
        if uploads is not None and not uploads.is_file():
            raise RestoreError(f"uploads archive not found: {uploads}")
    else:
        print("[dry-run] no database, volume, or file will be changed")

    base = compose_cmd(args)

    if args.drop_existing_scratch:
        run(
            base
            + [
                "exec",
                "-T",
                args.db_service,
                "dropdb",
                "-U",
                args.db_user,
                "--if-exists",
                args.target_db,
            ],
            execute=execute,
        )

    run(
        base
        + ["exec", "-T", args.db_service, "createdb", "-U", args.db_user, args.target_db],
        execute=execute,
    )

    if execute:
        with dump.open("rb") as handle:
            run(
                base
                + [
                    "exec",
                    "-T",
                    args.db_service,
                    "pg_restore",
                    "-U",
                    args.db_user,
                    "-d",
                    args.target_db,
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                ],
                execute=execute,
                stdin=handle,
            )
    else:
        print(f"[dry-run] would pipe {dump} into pg_restore -d {args.target_db}")

    for label, sql in CHECK_QUERIES:
        run(
            base
            + [
                "exec",
                "-T",
                args.db_service,
                "psql",
                "-U",
                args.db_user,
                "-d",
                args.target_db,
                "-At",
                "-c",
                sql,
            ],
            execute=execute,
            stdout=None,
        )
        print(f"[check] {label}: printed above")

    if uploads is not None:
        inspect_uploads_archive(uploads, execute)
        if args.uploads_target_volume:
            run(["docker", "volume", "create", args.uploads_target_volume], execute=execute)
            if execute:
                with uploads.open("rb") as handle:
                    run(
                        [
                            "docker",
                            "run",
                            "--rm",
                            "-i",
                            "-v",
                            f"{args.uploads_target_volume}:/data",
                            args.uploads_image,
                            "tar",
                            "-xzf",
                            "-",
                            "-C",
                            "/data",
                        ],
                        execute=execute,
                        stdin=handle,
                    )
            else:
                print(
                    f"[dry-run] would extract {uploads} into scratch volume "
                    f"{args.uploads_target_volume}"
                )

    if execute:
        print("[done] scratch restore complete; inspect it before cleanup")
        print(f"[cleanup] docker compose ... exec -T {args.db_service} dropdb -U {args.db_user} {args.target_db}")
        if args.uploads_target_volume:
            print(f"[cleanup] docker volume rm {args.uploads_target_volume}")
    else:
        print("[dry-run] no changes made")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RestoreError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
