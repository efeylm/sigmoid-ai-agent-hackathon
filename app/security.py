# Access control and cost protection
# - Access code: every /api request must carry a valid X-Access-Code header
#   (only enforced when APP_ACCESS_CODE is set, so local development stays open).
# - Daily limits: report generation is capped per client IP and in total,
#   so a leaked code cannot run up the OpenAI/Tavily bill.

import hmac
import threading
from collections import defaultdict
from datetime import date

from fastapi import Header, HTTPException, Request

from app.config import settings

ACCESS_CODE_HEADER = "X-Access-Code"


def _valid_codes() -> list[str]:
    return [c.strip() for c in (settings.APP_ACCESS_CODE or "").split(",") if c.strip()]


def access_code_required() -> bool:
    return bool(_valid_codes())


def is_valid_code(code: str | None) -> bool:
    if not code:
        return False
    return any(hmac.compare_digest(code.encode(), valid.encode()) for valid in _valid_codes())


async def require_access_code(
    x_access_code: str | None = Header(default=None, alias=ACCESS_CODE_HEADER),
) -> None:
    """FastAPI dependency: rejects the request unless it carries a valid access code."""
    if not access_code_required():
        return
    if not is_valid_code(x_access_code):
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik erişim kodu.")


def client_ip(request: Request) -> str:
    # Behind Caddy: Caddy replaces X-Forwarded-For from untrusted clients and
    # appends the real peer address, so the last entry is the client's IP.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class DailyLimiter:
    """In-memory per-day counters (the backend runs as a single process)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = date.today()
        self._per_ip: dict[str, int] = defaultdict(int)
        self._total = 0

    def _roll_day(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._per_ip.clear()
            self._total = 0

    def hit(self, ip: str) -> None:
        per_ip_limit = settings.REPORT_DAILY_LIMIT_PER_IP
        total_limit = settings.REPORT_DAILY_LIMIT_TOTAL
        with self._lock:
            self._roll_day()
            if total_limit > 0 and self._total >= total_limit:
                raise HTTPException(
                    status_code=429,
                    detail="Bugünkü toplam rapor limiti doldu. Lütfen yarın tekrar deneyin.",
                )
            if per_ip_limit > 0 and self._per_ip[ip] >= per_ip_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Günlük rapor limitinize ulaştınız ({per_ip_limit}). Lütfen yarın tekrar deneyin.",
                )
            self._per_ip[ip] += 1
            self._total += 1


report_limiter = DailyLimiter()


async def limit_costly_request(request: Request) -> None:
    """FastAPI dependency for endpoints that call OpenAI/Tavily."""
    report_limiter.hit(client_ip(request))
