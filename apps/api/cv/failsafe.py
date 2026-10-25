"""Fail-safe execution wrapper for CV modules (T064, FR-005, Constitution 2.II).

Guarantees that an uncaught exception or module timeout yields severity="warning"
with confidence=0.0 and degraded=True, never allowing an unhandled error to crash a run
or default to an "ok" status.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import ParamSpec, TypeVar

from rule_engine.config import apply_confidence_floor
from rule_engine.types import Finding, Measurement, Severity

log = logging.getLogger("launchguard.cv")
P = ParamSpec("P")
R = TypeVar("R", bound=list[Finding])

_executor = ThreadPoolExecutor(max_workers=4)


def failsafe(
    module: str,
    name: str,
    check_id: str,
    step_position: int = 1,
    timeout_s: float = 8.0,
) -> Callable[[Callable[P, list[Finding]]], Callable[P, list[Finding]]]:
    """Decorate a CV detection function to enforce fail-safe execution within timeout_s."""

    def decorator(fn: Callable[P, list[Finding]]) -> Callable[P, list[Finding]]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> list[Finding]:
            try:
                future = _executor.submit(fn, *args, **kwargs)
                findings = future.result(timeout=timeout_s)
                if not findings:
                    raise ValueError("Detector returned no findings")
                return [apply_confidence_floor(finding) for finding in findings]
            except FuturesTimeoutError:
                log.warning("CV module %s (%s) timed out after %.2f s", module, name, timeout_s)
                msg = f"{name} module timeout after {timeout_s:.1f} s; manual check required."
                return [
                    Finding(
                        module=module,
                        check_id=check_id,
                        severity=Severity.WARNING,
                        message=msg,
                        confidence=0.0,
                        metrics=(Measurement(name="timeout_s", value=timeout_s, unit="s"),),
                        step_position=step_position,
                        degraded=True,
                    )
                ]
            except Exception as exc:
                err_type = type(exc).__name__
                log.exception("CV module %s (%s) raised unhandled %s", module, name, err_type)
                msg = f"{name} could not be evaluated ({err_type}); manual check required."
                return [
                    Finding(
                        module=module,
                        check_id=check_id,
                        severity=Severity.WARNING,
                        message=msg,
                        confidence=0.0,
                        metrics=(Measurement(name="error", value=0.0, unit="status"),),
                        step_position=step_position,
                        degraded=True,
                    )
                ]

        return wrapper

    return decorator
