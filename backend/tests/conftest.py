"""Tests never touch the configured database.

Before: app.db read DATABASE_URL at import, so pytest wrote into whatever database the
machine was configured with, and the fixtures reset `risk.flag` to 0 and set
`entry.passed` to 1 in it. Set before any `app` import (conftest loads first).
"""
import os
import tempfile

_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="lumenia-tests-"), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")
