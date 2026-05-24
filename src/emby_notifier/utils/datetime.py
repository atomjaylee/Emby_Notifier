from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re


def iso8601_convert_cst(iso_time_str: str) -> datetime:
    utc_time = datetime.strptime(iso_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    cst_timezone = timezone(timedelta(hours=8))
    return utc_time.replace(tzinfo=timezone.utc).astimezone(cst_timezone)


def emby_version_at_least_4_8(version: str | None) -> bool:
    if not version:
        return False
    match = re.match(r"^(\d+)\.(\d+)", version)
    if not match:
        return False
    major, minor = map(int, match.groups())
    return major > 4 or (major == 4 and minor >= 8)


def parse_premiere_year(value: str | int | None, server_version: str | None) -> int:
    if value is None or value == "":
        return -1
    text = str(value)
    if text.isdigit():
        return int(text)
    if emby_version_at_least_4_8(server_version):
        return datetime.fromisoformat(text.replace("Z", "+00:00")).year
    return iso8601_convert_cst(text).year
