"""On-disk archive of raw emails: data/archive/<YYYY-MM-DD>/<source_id>/<gmail_msg_id>.eml

The date is the day the email was received in the editions' timezone (America/New_York).
The archive is keyed by source, not edition, because one email can serve two editions
(Semafor Business). Files are byte-exact copies of Gmail's raw RFC 822 message, written
atomically (temp file + rename) so a crash never leaves a half-written .eml.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import date
from pathlib import Path

_SAFE = re.compile(r"^[A-Za-z0-9_]+$")


def eml_relpath(day: date, source_id: str, msg_id: str) -> str:
    if not (_SAFE.match(source_id) and _SAFE.match(msg_id)):
        raise ValueError(f"unsafe archive path component: {source_id!r}/{msg_id!r}")
    return f"{day.isoformat()}/{source_id}/{msg_id}.eml"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_eml(archive_dir: Path, relpath: str, raw: bytes) -> str:
    """Write raw bytes atomically; returns their sha256. Idempotent for identical bytes."""
    target = archive_dir / relpath
    digest = sha256(raw)
    if target.is_file() and sha256(target.read_bytes()) == digest:
        return digest
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".eml")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return digest
