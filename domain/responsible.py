from __future__ import annotations

import re
import unicodedata
from uuid import UUID


_NAME_PARTICLES = {"da", "de", "do", "das", "dos", "e"}

_CANONICAL_RESPONSIBLES = {
    "alison": "Alison",
    "alison almeida": "Alison Almeida",
    "bruno pivoto": "Bruno Pivoto",
    "dafny peres": "Dafny Peres",
    "evandro": "Evandro",
    "fabricio": "Fabricio",
    "fagner": "Fagner",
    "fernando pozo": "Fernando Pozo",
    "jackson": "Jackson",
    "jc": "João Calheiros",
    "joao calheiros": "João Calheiros",
    "joao paulo": "João Paulo",
    "joao paulo bubicz": "João Paulo Bubicz",
    "laureane": "Laureane",
    "victor canellas": "Victor Canellas",
    "william": "William Rosa",
    "william rosa": "William Rosa",
}


def normalize_responsible_key(value: object) -> str:
    text = normalize_responsible_spaces(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_responsible_spaces(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ").strip())


def _title_word(word: str, index: int) -> str:
    lower_word = word.casefold()
    if index > 0 and lower_word in _NAME_PARTICLES:
        return lower_word
    if not word:
        return ""
    return word[0].upper() + word[1:].lower()


def _title_name(value: str) -> str:
    return " ".join(_title_word(word, index) for index, word in enumerate(value.split()))


def normalize_responsible_name(value: object) -> str:
    text = normalize_responsible_spaces(value)
    if not text:
        return ""

    key = normalize_responsible_key(text)
    if key in _CANONICAL_RESPONSIBLES:
        return _CANONICAL_RESPONSIBLES[key]

    return _title_name(text)


def is_uuid_text(value: object) -> bool:
    text = normalize_responsible_spaces(value)
    if not text:
        return False
    try:
        parsed = UUID(text)
    except (TypeError, ValueError):
        return False
    return str(parsed) == text.casefold()
