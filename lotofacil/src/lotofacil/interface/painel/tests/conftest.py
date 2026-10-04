"""Test-only setup for the dashboard test suite.

`server.py` now fails closed at import time: importing the module without
DASHBOARD_PASSWORD or DASHBOARD_PUBLICO=1 raises SystemExit (see
`_startup_auth_check` in server.py). This suite exercises the app directly
via Flask's test client without configuring either variable, so it opts
into DASHBOARD_SKIP_AUTH_CHECK=1 — a variable no Dockerfile/entrypoint in
this repo ever sets, so it has no effect outside test runs.

This must be set before any test module in this package imports
`lotofacil.interface.painel.server` for the first time, which is why it
lives in this package's conftest.py (pytest loads it before collecting the
sibling test modules).
"""
import os
import threading

import pytest

os.environ.setdefault("DASHBOARD_SKIP_AUTH_CHECK", "1")


@pytest.fixture(autouse=True)
def reset_dashboard_job_semaphore():
    """Keep process-local capacity isolated when tests stub thread startup."""
    from lotofacil.interface.painel import server

    yield
    server._job_semaphore = threading.Semaphore(server.DASHBOARD_MAX_JOBS)
