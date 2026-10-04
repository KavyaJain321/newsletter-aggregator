"""Byte-exact storage of original emails inside the database (table email_raw).

Raw RFC 822 messages are gzip-compressed (newsletter HTML shrinks ~5x) with a fixed header
(mtime 0) so the same email always compresses to the same bytes. `sha256` is taken over the
UNcompressed original, so integrity can be checked after any round trip.
"""
from __future__ import annotations

import gzip
import hashlib


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def unpack(blob: bytes | memoryview, expected_sha256: str | None = None) -> bytes:
    raw = gzip.decompress(bytes(blob))
    if expected_sha256 is not None and sha256(raw) != expected_sha256:
        raise ValueError("raw email failed its sha256 check")
    return raw
