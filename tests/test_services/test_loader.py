import pytest

from app.services.loader import CSVValidationError, parse_inventory

VALID_CSV = (
    b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    b"erp,web_app,linux,python,100,10.0,high,false,false\n"
)

MULTI_ROW_CSV = (
    b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    b"erp,web_app,linux,python,100,10.0,high,false,false\n"
    b"crm,database,windows,java,200,50.0,medium,true,false\n"
)


def test_valid_csv_parses():
    result = parse_inventory(VALID_CSV)
    assert len(result) == 1
    assert result[0].system_name == "erp"
    assert result[0].system_type.value == "web_app"
    assert result[0].num_users == 100


def test_multi_row_csv_parses():
    result = parse_inventory(MULTI_ROW_CSV)
    assert len(result) == 2
    assert result[0].system_name == "erp"
    assert result[1].system_name == "crm"


def test_invalid_csv_raises_with_row_numbers():
    bad = (
        b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
        b"erp,INVALID,linux,python,100,10.0,high,false,false\n"
    )
    with pytest.raises(CSVValidationError) as exc_info:
        parse_inventory(bad)
    assert any("row" in str(e).lower() or "2" in str(e) for e in exc_info.value.errors)


def test_duplicate_system_names_raises():
    dup = VALID_CSV + b"erp,web_app,linux,python,50,5.0,low,false,false\n"
    with pytest.raises(CSVValidationError) as exc_info:
        parse_inventory(dup)
    assert any("duplicate" in e.lower() for e in exc_info.value.errors)


def test_exceeding_1000_rows_raises():
    header = b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    row = b"sys_%d,web_app,linux,python,10,1.0,low,false,false\n"
    data = header + b"".join(row.replace(b"%d", str(i).encode()) for i in range(1001))
    with pytest.raises((CSVValidationError, ValueError)):
        parse_inventory(data)