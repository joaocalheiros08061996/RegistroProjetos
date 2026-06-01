from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Iterable


DEFAULT_MAX_INPUT_FILE_BYTES = 50 * 1024 * 1024


def configured_max_input_file_bytes() -> int:
    raw_value = os.getenv("AUTOMACAO_MAX_INPUT_FILE_BYTES", "").strip()
    if not raw_value:
        return DEFAULT_MAX_INPUT_FILE_BYTES
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_MAX_INPUT_FILE_BYTES
    return value if value > 0 else DEFAULT_MAX_INPUT_FILE_BYTES


def validate_input_file(
    path: Path,
    *,
    allowed_suffixes: Iterable[str],
    max_bytes: int | None = None,
    description: str = "Arquivo",
) -> Path:
    resolved = Path(path).expanduser()
    suffixes = {suffix.lower() for suffix in allowed_suffixes}
    if resolved.suffix.lower() not in suffixes:
        allowed = ", ".join(sorted(suffixes))
        raise ValueError(f"{description} com extensao invalida: {resolved}. Permitidas: {allowed}")

    try:
        file_stat = resolved.stat()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"{description} nao encontrado: {resolved}") from exc

    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(f"{description} deve ser um arquivo regular: {resolved}")

    size_limit = configured_max_input_file_bytes() if max_bytes is None else max_bytes
    if file_stat.st_size > size_limit:
        raise ValueError(
            f"{description} excede o tamanho maximo de {size_limit} bytes: {resolved}"
        )

    return resolved.resolve()


def validate_optional_input_file(
    path: Path,
    *,
    allowed_suffixes: Iterable[str],
    max_bytes: int | None = None,
    description: str = "Arquivo",
) -> Path:
    candidate = Path(path).expanduser()
    suffixes = {suffix.lower() for suffix in allowed_suffixes}
    if candidate.suffix.lower() not in suffixes:
        allowed = ", ".join(sorted(suffixes))
        raise ValueError(f"{description} com extensao invalida: {candidate}. Permitidas: {allowed}")
    if not candidate.exists():
        return candidate
    return validate_input_file(
        candidate,
        allowed_suffixes=suffixes,
        max_bytes=max_bytes,
        description=description,
    )
