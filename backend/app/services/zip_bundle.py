from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


def build_zip_bundle(files: list[tuple[str, bytes]]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for filename, content in files:
            archive.writestr(filename, content)
    return buffer.getvalue()
