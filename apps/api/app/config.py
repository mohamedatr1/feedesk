from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_name: str = "FeeDesk"
    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:55432/feedesk"
    session_secret: str = "dev-only-change-me"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    upload_dir: str = str(ROOT / ".local" / "uploads")
    upload_max_bytes: int = 20 * 1024 * 1024
    import_max_rows: int = 5000
    import_max_pages: int = 200
    # Assisted OCR for scanned PDF imports. Rows produced by OCR still require
    # normal validation and human review; nothing is auto-confirmed.
    ocr_enabled: bool = True
    ocr_tesseract_cmd: str = "tesseract"
    ocr_tessdata_dir: str = ""
    ocr_languages: str = "ara+eng"
    ocr_render_dpi: int = 300
    ocr_min_confidence: float = 50
    ocr_max_pages: int = 20
    ocr_timeout_seconds: int = 120
    # XLSX archives are zip files: bound decompression before any parsing so a
    # crafted workbook cannot exhaust memory or disk during import.
    xlsx_max_uncompressed_bytes: int = 200 * 1024 * 1024
    xlsx_max_member_bytes: int = 100 * 1024 * 1024
    xlsx_max_compression_ratio: float = 100.0
    xlsx_max_members: int = 10000
    log_level: str = "INFO"

    cookie_name: str = "fd_session"
    cookie_secure: bool = False
    session_hours: int = 8
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60
    login_lockout_threshold: int = 5
    login_lockout_minutes: int = 15
    # Enable only behind a trusted reverse proxy that overwrites X-Forwarded-For.
    trust_forwarded_for: bool = False

    rasel_api_key: str = ""
    rasel_base_url: str = "https://raselsms.com"
    rasel_channel: str = "local_sms"
    rasel_sender_id: str = ""
    # Fernet key used to encrypt provider credentials at rest. Empty in
    # development; production refuses to start without a valid key.
    provider_credential_key: str = ""

    # Messaging safety defaults: no provider traffic unless explicitly enabled.
    messaging_provider: str = "fake"
    messaging_enabled: bool = False
    messaging_kill_switch: bool = True
    messaging_rate_limit_per_second: float = 1.0
    messaging_max_attempts: int = 3
    messaging_lease_seconds: int = 60
    messaging_allowlist: str = ""
    # Per-actor throttle for the dry-run test-send endpoint. Counted from the
    # append-only ``messaging.test_send`` audit trail, so it survives restarts.
    messaging_test_send_limit: int = 5
    messaging_test_send_window_seconds: int = 60
    # Fake delivery must never be mistaken for real delivery in production.
    messaging_allow_fake_in_production: bool = False
    fake_provider_scenario: str = "delivered"

    seed_admin_username: str = "admin"
    seed_admin_password: str = "ChangeMe!2026"
    # Escape hatch for non-production environments that intentionally seed the
    # default temporary password (for example an isolated CI database). Never
    # enable this in production; the production validator below still refuses
    # the default password regardless of this flag.
    seed_allow_default_password: bool = False
    seed_school_name: str = "مدرسة الروض الخاصة"
    seed_currency: str = "SYP"
    seed_currency_symbol: str = "د.س"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_driver(cls, value: object) -> object:
        """Accept managed-provider URLs that omit the SQLAlchemy driver.

        Neon and other marketplace providers inject ``postgresql://...`` (and
        sometimes ``postgres://...``).  The project deliberately uses psycopg 3,
        so normalize the scheme instead of requiring a duplicate environment
        variable override in Vercel.
        """
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.app_env.lower() == "production":
            if (
                self.session_secret == "dev-only-change-me"
                or len(self.session_secret) < 32
            ):
                raise ValueError(
                    "SESSION_SECRET must be a unique value of at least 32 characters in production."
                )
            if self.seed_admin_password == "ChangeMe!2026":
                raise ValueError(
                    "SEED_ADMIN_PASSWORD must be set to a non-default value in production."
                )
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production.")
            if not self.cookie_name.startswith("__Host-"):
                raise ValueError(
                    "COOKIE_NAME must use the __Host- prefix in production."
                )
            if not self.app_base_url.lower().startswith("https://"):
                raise ValueError("APP_BASE_URL must use https:// in production.")
            credential_key = (self.provider_credential_key or "").strip()
            if not credential_key:
                raise ValueError(
                    "PROVIDER_CREDENTIAL_KEY must be a Fernet key in production."
                )
            try:
                Fernet(credential_key.encode("utf-8"))
            except (TypeError, ValueError):
                raise ValueError(
                    "PROVIDER_CREDENTIAL_KEY must be a Fernet key in production."
                ) from None
            if self.messaging_enabled:
                provider = (self.messaging_provider or "").strip().lower()
                if provider not in {"fake", "rasel"}:
                    raise ValueError(
                        "MESSAGING_PROVIDER must be 'fake' or 'rasel' in production."
                    )
                if provider == "fake" and not self.messaging_allow_fake_in_production:
                    raise ValueError(
                        "MESSAGING_PROVIDER=fake is refused in production without "
                        "MESSAGING_ALLOW_FAKE_IN_PRODUCTION."
                    )
                if self.messaging_rate_limit_per_second <= 0:
                    raise ValueError(
                        "MESSAGING_RATE_LIMIT_PER_SECOND must be greater than zero in production."
                    )
        return self


settings = Settings()
