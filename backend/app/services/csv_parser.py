import csv
import io


class CsvParseError(ValueError):
    pass


def decode_csv_content(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvParseError("CSV file must be UTF-8 encoded.") from exc


def parse_csv_rows(content: str) -> list[dict[str, str]]:
    if not content.strip():
        raise CsvParseError("CSV file is empty.")

    stream = io.StringIO(content, newline="")
    reader = csv.DictReader(stream)

    if reader.fieldnames is None:
        raise CsvParseError("CSV file must include a header row.")

    normalized_headers = [header.strip() if header else "" for header in reader.fieldnames]
    if any(not header for header in normalized_headers):
        raise CsvParseError("CSV headers must not be empty.")

    reader.fieldnames = normalized_headers
    rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]

    if not rows:
        raise CsvParseError("CSV file must include at least one data row.")

    return rows
