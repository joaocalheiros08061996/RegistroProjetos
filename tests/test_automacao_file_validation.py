import pytest

from automacoes.file_validation import validate_input_file


def test_validate_input_file_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="nao encontrado"):
        validate_input_file(
            tmp_path / "missing.xlsx",
            allowed_suffixes={".xlsx"},
            description="Planilha",
        )


def test_validate_input_file_rejects_invalid_extension(tmp_path):
    path = tmp_path / "dados.txt"
    path.write_text("conteudo", encoding="utf-8")

    with pytest.raises(ValueError, match="extensao invalida"):
        validate_input_file(
            path,
            allowed_suffixes={".csv"},
            description="CSV",
        )


def test_validate_input_file_rejects_file_above_limit(tmp_path):
    path = tmp_path / "dados.json"
    path.write_text("12345", encoding="utf-8")

    with pytest.raises(ValueError, match="tamanho maximo"):
        validate_input_file(
            path,
            allowed_suffixes={".json"},
            max_bytes=4,
            description="JSON",
        )
