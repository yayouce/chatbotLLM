
import datetime
from typing import Optional
def is_within_time_range(log_timestamp_str: str, start_time_str: Optional[str], end_time_str: Optional[str]) -> bool:
    if not start_time_str and not end_time_str:
        return True # Pas de filtre de temps

    log_dt = datetime.fromisoformat(log_timestamp_str.replace('Z', '+00:00'))

    if start_time_str:
        start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        if log_dt < start_dt:
            return False
    if end_time_str:
        end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        if log_dt > end_dt:
            return False
    return True
