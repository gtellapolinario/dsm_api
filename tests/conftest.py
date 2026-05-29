"""Pytest compatibility helpers for async tests in minimal environments."""
from __future__ import annotations

import asyncio
import inspect


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run async test with asyncio")


def pytest_pyfunc_call(pyfuncitem):
    if "asyncio" not in pyfuncitem.keywords:
        return None
    testfunction = pyfuncitem.obj
    if not inspect.iscoroutinefunction(testfunction):
        return None
    kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    asyncio.run(testfunction(**kwargs))
    return True
