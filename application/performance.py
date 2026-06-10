import logging
import os
import time

logger = logging.getLogger(__name__)


def perf_diagnostics_enabled() -> bool:
    return os.getenv("PERF_DIAGNOSTICS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def log_perf(operation: str, started_at: float, **fields) -> None:
    if not perf_diagnostics_enabled():
        return

    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    logger.info(
        "perf operation=%s elapsed_ms=%.2f fields=%s",
        operation,
        elapsed_ms,
        fields,
    )
