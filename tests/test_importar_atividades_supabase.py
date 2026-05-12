import json
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from automacoes.importar_atividades_supabase import (
    ActivityRecord,
    UserMapping,
    calculated_hours,
    load_manifest,
    load_user_map,
    parse_activities,
    parse_datetime,
    stable_natural_key,
)


TZ = ZoneInfo("America/Sao_Paulo")


def test_parse_datetime_treats_naive_csv_value_as_sao_paulo():
    parsed = parse_datetime("2025-09-11 07:52:18.118038")

    assert parsed == datetime(2025, 9, 11, 7, 52, 18, 118038, tzinfo=TZ)


def test_calculated_hours_matches_duration_when_csv_hours_are_missing():
    start = datetime(2025, 9, 11, 8, 0, tzinfo=TZ)
    end = datetime(2025, 9, 11, 9, 30, tzinfo=TZ)

    assert calculated_hours(start, end) == Decimal("1.5000000000")


def test_parse_activities_preserves_historical_type_and_maps_user():
    rows = [
        {
            "id": "4",
            "tipo_atividade": "Documentação",
            "descricao": "Atualização das métricas",
            "inicio": "2025-09-11 08:00:00",
            "fim": "2025-09-11 09:30:00",
            "user_id": "JACKSON",
            "ano": "2025",
            "mes": "9",
            "dia": "11",
            "horas_trabalhadas": "",
        }
    ]
    user_map = {
        "jackson": UserMapping(
            source_label="JACKSON",
            user_id="uuid-jackson",
            responsavel="Jackson",
        )
    }

    parsed = parse_activities(rows, user_map)

    assert not parsed.skipped
    assert len(parsed.records) == 1
    record = parsed.records[0]
    assert record.user_id == "uuid-jackson"
    assert record.responsavel == "Jackson"
    assert record.tipo_atividade == "Documentação"
    assert record.horas_trabalhadas == Decimal("1.5000000000")


def test_parse_activities_skips_open_bad_and_unmapped_rows():
    base = {
        "descricao": "Desc",
        "inicio": "2025-09-11 08:00:00",
        "fim": "2025-09-11 09:00:00",
        "ano": "2025",
        "mes": "9",
        "dia": "11",
        "horas_trabalhadas": "1",
    }
    rows = [
        {**base, "id": "1", "tipo_atividade": "Cadastro", "user_id": "Mapeado", "fim": ""},
        {**base, "id": "2", "tipo_atividade": "Cadastro", "user_id": "Sem mapa"},
        {**base, "id": "3", "tipo_atividade": "Cadastro", "user_id": "Mapeado", "inicio": "x"},
    ]
    user_map = {
        "mapeado": UserMapping(
            source_label="Mapeado",
            user_id="uuid-mapeado",
            responsavel="Mapeado",
        )
    }

    parsed = parse_activities(rows, user_map)

    assert not parsed.records
    assert [item["reason"] for item in parsed.skipped] == [
        "open_activity",
        "missing_user_mapping",
        "invalid_start_datetime",
    ]


def test_user_map_ignores_entries_without_uuid(tmp_path):
    path = tmp_path / "map.json"
    path.write_text(
        json.dumps(
            {
                "users": {
                    "A": {"user_id": "", "responsavel": "A"},
                    "B": {"user_id": "uuid-b", "responsavel": "B"},
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = load_user_map(path)

    assert set(loaded) == {"b"}
    assert loaded["b"].user_id == "uuid-b"


def test_manifest_defaults_and_natural_key_are_stable(tmp_path):
    manifest = load_manifest(tmp_path / "missing.json")
    assert manifest == {"version": 1, "activities": {}}

    record = ActivityRecord(
        source_id="10",
        source_user_label="João",
        user_id="uuid-joao",
        responsavel="João",
        tipo_atividade="Cadastro",
        descricao="Registro",
        inicio=datetime(2025, 9, 11, 8, 0, tzinfo=TZ),
        fim=datetime(2025, 9, 11, 9, 0, tzinfo=TZ),
        ano=2025,
        mes=9,
        dia=11,
        horas_trabalhadas=Decimal("1.0"),
    )

    key = stable_natural_key(record)
    assert key[0] == "uuid-joao"
    assert key[1] == "Cadastro"
    assert key[4] == "Registro"
