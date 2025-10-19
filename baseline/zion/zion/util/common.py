from datetime import datetime

import pytz

from zion.util.aws.constant import (
    DEFAULT_TIMEZONE_REGION,
)


def get_current_time_in_iso8601_sgt() -> str:
    current_time = datetime.now(pytz.timezone(DEFAULT_TIMEZONE_REGION))
    return current_time.isoformat()
