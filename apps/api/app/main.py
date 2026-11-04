from __future__ import annotations

import json
import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .errors import ApiError
from .redaction import redact_text
from .routers import (
    audit,
    auth,
    campaigns,
    dashboard,
    files,
    health,
    imports,
    messages,
    messaging_control,
    messaging_ops,
    templates,
    users,
)
from .routers import settings as settings_router


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level.upper(), handlers=[handler], force=True)
logger = logging.getLogger("feedesk.api")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def _request_id(request: Request) -> str:
    candidate = request.headers.get("x-request-id")
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())

@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="FeeDesk API",
    version="0.1.0",
    docs_url="/api/docs" if settings.app_env.lower() != "production" else None,
    openapi_url="/api/openapi.json" if settings.app_env.lower() != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if request.url.path.startswith("/api/v1"):
        # Authenticated API payloads and file downloads must never be cached
        # by browsers or intermediary proxies.
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = _request_id(request)
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed", extra={"request_id": request_id})
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s %s %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )
    return response


def error_payload(request: Request, code: str, message_ar: str, message_en: str, details=None):
    return {
        "error": {
            "code": code,
            "message_ar": message_ar,
            "message_en": message_en,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, exc.code, exc.message_ar, exc.message_en, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    details = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload(
            request,
            "VALIDATION_ERROR",
            "البيانات المرسلة غير صالحة.",
            "Request validation failed.",
            details,
        ),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            request,
            "HTTP_ERROR",
            "تعذر تنفيذ الطلب.",
            str(exc.detail) if exc.detail else "Request failed.",
        ),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled error", extra={"request_id": getattr(request.state, "request_id", None)})
    return JSONResponse(
        status_code=500,
        content=error_payload(
            request,
            "INTERNAL_ERROR",
            "حدث خطأ غير متوقع. حاول لاحقًا.",
            "An unexpected error occurred.",
        ),
    )


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(messaging_control.router, prefix="/api/v1")
app.include_router(messaging_ops.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "FeeDesk API", "version": "0.1.0", "docs": "/api/docs"}
