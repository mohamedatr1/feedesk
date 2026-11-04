from __future__ import annotations

import argparse
import logging
import signal
import threading

from .config import settings
from .db import SessionLocal
from .messaging.credentials import credential_status
from .messaging.factory import provider_name, transport_configuration_error
from .messaging.worker import MessagingWorker


def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _log_startup() -> None:
    logger = logging.getLogger("feedesk.worker")
    # Only credential metadata is logged: never the key, sender, or ciphertext.
    try:
        with SessionLocal() as db:
            credential = credential_status(db)
    except Exception:
        credential = {
            "credential_source": "unavailable",
            "configured": False,
            "key_version": None,
        }
    logger.info(
        "worker.start provider=%s enabled=%s kill_switch=%s rate_per_second=%s "
        "max_attempts=%s credential_source=%s credential_configured=%s key_version=%s",
        provider_name(settings),
        bool(settings.messaging_enabled),
        bool(settings.messaging_kill_switch),
        settings.messaging_rate_limit_per_second,
        settings.messaging_max_attempts,
        credential.get("credential_source"),
        bool(credential.get("configured")),
        credential.get("key_version"),
    )
    error = transport_configuration_error(settings)
    if error:
        logger.warning("worker.config provider_unusable reason=%s", error)
    elif provider_name(settings) != "fake" and not credential.get("configured"):
        logger.warning("worker.config provider_credential_unavailable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.worker",
        description="FeeDesk messaging worker. The API process never sends messages.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Claim and process at most one due job, then exit.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds to wait when no job is due (loop mode).",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=None,
        help="Stop after processing this many jobs (loop mode).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging()
    _log_startup()
    logger = logging.getLogger("feedesk.worker")

    worker = MessagingWorker(config=settings)
    if args.once:
        report = worker.run_once()
        logger.info(
            "worker.once claimed=%s job_id=%s message_id=%s outcome=%s skipped=%s",
            report.claimed,
            report.job_id,
            report.message_id,
            report.outcome,
            report.skipped_reason,
        )
        return 0

    stop_event = threading.Event()

    def _handle_signal(_signum: int, _frame: object) -> None:
        logger.info("worker.stop_requested")
        stop_event.set()
        worker.request_stop()

    for signal_name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, signal_name):
            try:
                signal.signal(getattr(signal, signal_name), _handle_signal)
            except (ValueError, OSError):
                pass

    try:
        result = worker.run_loop(
            stop_event=stop_event,
            poll_interval=args.poll_interval,
            max_jobs=args.max_jobs,
        )
    except KeyboardInterrupt:
        stop_event.set()
        worker.request_stop()
        result = worker.run_loop(stop_event=stop_event, max_jobs=0)
    logger.info(
        "worker.loop stopped claimed=%s outcomes=%s",
        result.claimed,
        result.outcomes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
