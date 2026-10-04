"""Recover a JSON value from raw LLM output.

Handles: <think>…</think> reasoning blocks, markdown code fences, prose before or
after the JSON, trailing commas, and output truncated mid-value (closes open
strings/containers, dropping the last incomplete element). It never invents
content: if no JSON value can be recovered it raises JSONRepairError.

Idea credit: fence stripping + truncation repair as in not-indro/AI-Weekly-Digest
`summarize._parse_json` (MIT). This is an independent, string-aware implementation.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

_THINK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\s*\n?(.*?)```", re.S)
_CLOSER = {"{": "}", "[": "]"}
_MAX_BACKTRACK = 200


class JSONRepairError(ValueError):
    pass


def strip_reasoning(text: str) -> str:
    """Remove <think> blocks; an unterminated <think> means no answer was produced."""
    text = _THINK_RE.sub("", text)
    if re.search(r"<think>", text, re.I):
        text = re.split(r"<think>", text, flags=re.I)[0]
    return text.strip()


def _remove_trailing_commas(s: str) -> str:
    out: list[str] = []
    in_str = esc = False
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif c == ",":
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] in "}]":
                i += 1
                continue
            out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _extract_value(s: str) -> tuple[str, bool]:
    """Return (text from the first { or [ to its matching close, balanced?)."""
    start = min((i for i in (s.find("{"), s.find("[")) if i != -1), default=-1)
    if start == -1:
        raise JSONRepairError("no JSON object or array found in output")
    stack: list[str] = []
    in_str = esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c in "}]":
            if not stack or _CLOSER[stack[-1]] != c:
                return s[start:i], False  # mismatched closer: treat as truncated here
            stack.pop()
            if not stack:
                return s[start:i + 1], True
    return s[start:], False


def _close_truncated(s: str) -> str:
    """Close an unbalanced prefix; backtrack to the last complete element if needed."""
    candidate = s
    for _ in range(_MAX_BACKTRACK):
        stack: list[str] = []
        in_str = esc = False
        boundaries: list[int] = []  # commas / container opens outside strings
        for i, c in enumerate(candidate):
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c in "{[":
                stack.append(c)
                boundaries.append(i + 1)
            elif c in "}]":
                if stack:
                    stack.pop()
            elif c == ",":
                boundaries.append(i)
        body = candidate + ('"' if in_str else "")
        body = body.rstrip()
        if body.endswith(","):
            body = body[:-1]
        elif body.endswith(":"):
            body += " null"
        attempt = _remove_trailing_commas(body + "".join(_CLOSER[o] for o in reversed(stack)))
        try:
            json.loads(attempt)
            return attempt
        except json.JSONDecodeError:
            pass
        cut = max((b for b in boundaries if b < len(candidate)), default=-1)
        if cut <= 0:
            break
        candidate = candidate[:cut]
    raise JSONRepairError("could not close truncated JSON")


def parse_json(text: str, expect: Literal["object", "array"] | None = None) -> Any:
    """Parse JSON from raw model output, repairing common damage. Raises JSONRepairError."""
    if text is None or not text.strip():
        raise JSONRepairError("empty output")
    body = strip_reasoning(text)
    fenced = [m.group(1) for m in _FENCE_RE.finditer(body) if re.search(r"[\[{]", m.group(1))]
    if fenced:
        body = fenced[0]
    body = body.strip()

    value: Any
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        chunk, balanced = _extract_value(body)
        chunk = _remove_trailing_commas(chunk)
        if balanced:
            try:
                value = json.loads(chunk)
            except json.JSONDecodeError as e:
                raise JSONRepairError(f"invalid JSON after cleanup: {e.msg} at {e.pos}") from e
        else:
            value = json.loads(_close_truncated(chunk))

    if expect == "object" and not isinstance(value, dict):
        raise JSONRepairError(f"expected a JSON object, got {type(value).__name__}")
    if expect == "array" and not isinstance(value, list):
        raise JSONRepairError(f"expected a JSON array, got {type(value).__name__}")
    return value
