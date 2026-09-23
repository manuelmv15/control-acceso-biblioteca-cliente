from datetime import datetime
from zoneinfo import ZoneInfo

TZ_SV = ZoneInfo("America/El_Salvador")


def now_sv() -> datetime:
    return datetime.now(TZ_SV)
