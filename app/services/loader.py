import csv
import io
from collections import Counter

from app.schemas import SystemInventory


class CSVValidationError(Exception):
    """Raised when CSV data fails validation, carrying structured error details."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("CSV validation failed")


def parse_inventory(data: bytes) -> list[SystemInventory]:
    """Parse and validate a CSV inventory file, returning a list of SystemInventory objects.

    Raises CSVValidationError if any rows are invalid or duplicate system names are found.
    Raises ValueError if the CSV exceeds 1,000 data rows.
    """
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    errors: list[str] = []
    systems: list[SystemInventory] = []

    for row_num, row in enumerate(reader, start=2):  # row 1 is header, data starts at 2
        # Enforce 1,000 row limit
        if len(systems) >= 1000:
            raise ValueError("CSV exceeds maximum of 1,000 rows")

        try:
            system = SystemInventory.model_validate(row)
            systems.append(system)
        except Exception as e:
            errors.append(f"Row {row_num}: {e}")

    # Check for duplicate system names
    name_counts = Counter(s.system_name for s in systems)
    duplicates = [name for name, count in name_counts.items() if count > 1]
    for dup in duplicates:
        errors.append(f"Duplicate system_name '{dup}' found")

    if errors:
        raise CSVValidationError(errors)

    return systems