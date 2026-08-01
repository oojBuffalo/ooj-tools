"""Small, shared JSON I/O primitives for plugin-configure."""

import json
import os
import tempfile


JSON_READ_ERRORS = (OSError, UnicodeError, json.JSONDecodeError, RecursionError)


def read_json(path):
    """Read a UTF-8 JSON document, tolerating an optional byte-order mark."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path, data):
    """Write JSON atomically using a temporary file beside the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_path, str(path))
    except BaseException:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise
