from domain.responsible import (
    is_uuid_text,
    normalize_responsible_key,
    normalize_responsible_name,
)


def test_normalize_responsible_name_applies_canonical_names():
    assert normalize_responsible_name(" JACKSON ") == "Jackson"
    assert normalize_responsible_name("fagner") == "Fagner"
    assert normalize_responsible_name("JOÃO PAULO") == "João Paulo"
    assert normalize_responsible_name("jc") == "João Calheiros"
    assert normalize_responsible_name("William") == "William Rosa"


def test_normalize_responsible_name_title_cases_unknown_names():
    assert normalize_responsible_name("maria da silva") == "Maria da Silva"
    assert normalize_responsible_name("  BRUNO   PIVOTO ") == "Bruno Pivoto"


def test_normalize_responsible_key_ignores_case_and_accents():
    assert normalize_responsible_key("João Calheiros") == "joao calheiros"


def test_is_uuid_text_identifies_real_uuids():
    assert is_uuid_text("3a57b554-346e-492f-88a4-f1dbb7d5ba77")
    assert not is_uuid_text("JACKSON")
