from __future__ import annotations

import logging

import pytest
from sqlalchemy import text

from app.db import SessionLocal

PHONE = "+963993000777"
BODY = "رسالة سرية تحتوي رصيدًا ماليًا"


def test_forced_db_error_hides_bound_parameter_values(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="sqlalchemy.engine"):
        with SessionLocal() as db:
            with pytest.raises(Exception) as excinfo:
                db.execute(
                    text("SELECT :phone, :body FROM feedesk_table_that_does_not_exist"),
                    {"phone": PHONE, "body": BODY},
                )
            db.rollback()

    observed = caplog.text + "\n" + str(excinfo.value)
    assert PHONE not in observed
    assert BODY not in observed
    assert "SQL parameters hidden" in observed
