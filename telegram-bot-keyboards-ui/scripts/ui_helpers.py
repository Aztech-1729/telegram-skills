"""Offline UI primitives. Authorization belongs to the caller, not callback text."""
from __future__ import annotations

import math
import re
from collections.abc import Sequence

_CALLBACK = re.compile(r"v1:(page|item|confirm|cancel):([0-9]{1,18})\Z", re.ASCII)


def check_callback(data: str) -> str:
    if not isinstance(data, str) or not 1 <= len(data.encode("utf-8")) <= 64:
        raise ValueError("callback_data must contain 1–64 UTF-8 bytes")
    return data


def parse_callback(data: str) -> tuple[str, int]:
    check_callback(data)
    match = _CALLBACK.fullmatch(data)
    if match is None:
        raise ValueError("unknown callback schema")
    return match[1], int(match[2])


def utf16_range(text: str, start: int, end: int) -> tuple[int, int]:
    """Map Python character boundaries to Telegram entity offset/length."""
    if not 0 <= start < end <= len(text):
        raise ValueError("non-empty range must be inside text")
    offset = len(text[:start].encode("utf-16-le")) // 2
    length = len(text[start:end].encode("utf-16-le")) // 2
    return offset, length


def page_rows(items: Sequence[tuple[int, str]], page: int, size: int = 5):
    """Return clamped page and raw Bot API rows; IDs must be caller-authorized."""
    if type(page) is not int or type(size) is not int or size <= 0:
        raise ValueError("page and positive size must be integers")
    pages = max(1, math.ceil(len(items) / size))
    page = min(max(0, page), pages - 1)
    rows = []
    for record_id, label in items[page * size:(page + 1) * size]:
        if type(record_id) is not int or not 0 <= record_id < 10**18:
            raise ValueError("invalid record ID")
        rows.append([{"text": label, "callback_data": check_callback(f"v1:item:{record_id}")}])
    nav = []
    if page:
        nav.append({"text": "Previous", "callback_data": check_callback(f"v1:page:{page - 1}")})
    if page + 1 < pages:
        nav.append({"text": "Next", "callback_data": check_callback(f"v1:page:{page + 1}")})
    if nav:
        rows.append(nav)
    return page, rows
