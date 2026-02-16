import pytest

from nexo_tax.api import REQUIRED_COLUMNS, validate_csv_schema

VALID_HEADER = (
    "Transaction,Type,Input Currency,Input Amount,Output Currency,"
    "Output Amount,USD Equivalent,Fee,Fee Currency,Details,Date / Time (UTC)\n"
)


def test_valid_schema_passes() -> None:
    validate_csv_schema(VALID_HEADER)


def test_empty_csv_raises() -> None:
    with pytest.raises(ValueError, match="empty or has no header row"):
        validate_csv_schema("")


def test_missing_single_column_raises() -> None:
    header = VALID_HEADER.replace("Transaction,", "")
    with pytest.raises(ValueError, match="Transaction"):
        validate_csv_schema(header)


def test_missing_multiple_columns_raises() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        validate_csv_schema("SomeOtherColumn,AnotherColumn\n")


def test_all_required_columns_present() -> None:
    # Ensure REQUIRED_COLUMNS matches what parse_csv_from_string accesses
    assert "Date / Time (UTC)" in REQUIRED_COLUMNS
    assert "Transaction" in REQUIRED_COLUMNS
    assert "Type" in REQUIRED_COLUMNS
    assert "USD Equivalent" in REQUIRED_COLUMNS


def test_extra_columns_allowed() -> None:
    header = VALID_HEADER.rstrip("\n") + ",ExtraColumn\n"
    validate_csv_schema(header)
