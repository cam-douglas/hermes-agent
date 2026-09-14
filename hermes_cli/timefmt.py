"""Small shared time-formatting helpers for CLI output.

Session-list clocks on this VPS are Australia/Sydney in Cam's stamp:
``dd:mm:yy hh:mm:ss``.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SYDNEY_TZ = ZoneInfo("Australia/Sydney")
# day:month:year hours:minutes:seconds (AEST/AEDT)
SYDNEY_STAMP = "%d:%m:%y %H:%M:%S"


def format_sydney(ts=None) -> str:
    """Render *ts* (unix seconds) or now as Australia/Sydney ``SYDNEY_STAMP``."""
    if ts in (None, "", 0):
        if ts in (None, ""):
            dt = datetime.now(SYDNEY_TZ)
        else:
            dt = datetime.fromtimestamp(0, tz=SYDNEY_TZ)
    else:
        try:
            dt = datetime.fromtimestamp(float(ts), tz=SYDNEY_TZ)
        except (TypeError, ValueError, OSError, OverflowError):
            return "?"
    return dt.strftime(SYDNEY_STAMP)


def relative_time(ts) -> str:
    """Session-list last-active stamp (Sydney). ``?`` when *ts* is missing."""
    if not ts:
        return "?"
    return format_sydney(ts)
