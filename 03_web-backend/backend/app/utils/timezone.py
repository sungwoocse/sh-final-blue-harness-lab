"""시간대 관련 유틸리티 (KST 기준)"""
from datetime import datetime, timezone, timedelta

# 한국 표준시 UTC+9
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """KST 기준의 timezone-aware 현재 시각을 반환"""
    return datetime.now(tz=KST)


def now_kst_iso() -> str:
    """KST 기준 ISO8601 문자열(+09:00 오프셋 포함)을 반환"""
    return now_kst().isoformat()


def to_kst(dt: datetime) -> datetime:
    """
    주어진 datetime을 KST로 변환.
    naive인 경우 UTC 기준으로 간주한 뒤 KST로 변환한다.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)
