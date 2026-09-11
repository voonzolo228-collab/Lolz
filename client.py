"""
HTTP-клієнт для MRKT API з rate limiting, retry/backoff, пагінацією
через cursor і коротким in-memory кешем, щоб не дублювати однакові
запити протягом одного циклу моніторингу.
"""
import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from mrkt.auth import MrktAuth, MrktAuthError
from mrkt.models import Gift

logger = logging.getLogger("mrkt.client")

MAX_PAGE_SIZE = 20  # підтверджений ліміт API (count)


class MrktApiError(RuntimeError):
    pass


class MrktClient:
    def __init__(self, api_base: str, auth: MrktAuth, min_request_interval: float = 0.5):
        self._api_base = api_base.rstrip("/")
        self._auth = auth
        self._min_request_interval = min_request_interval
        self._last_request_ts = 0.0
        self._lock = asyncio.Lock()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 5.0  # секунд - захист від дублюючих запитів в одному циклі

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_request_interval - (now - self._last_request_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_ts = time.monotonic()

    async def _post(self, path: str, json_body: dict[str, Any], retries: int = 4) -> dict[str, Any]:
        cache_key = f"{path}:{json_body}"
        cached = self._cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < self._cache_ttl:
            return cached[1]

        if not self._auth.token:
            await self._auth.refresh_token()

        backoff = 1.0
        last_error: Optional[Exception] = None

        for attempt in range(retries):
            await self._throttle()
            headers = {
                "Authorization": self._auth.token,
                "Referer": "https://cdn.tgmrkt.io/",
                "Content-Type": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        f"{self._api_base}{path}", headers=headers, json=json_body
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                logger.warning("MRKT request timeout/transport error (спроба %s): %s", attempt + 1, exc)
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code == 401:
                logger.info("MRKT token прострочений (401). Оновлюю токен...")
                try:
                    await self._auth.refresh_token()
                except MrktAuthError as exc:
                    last_error = exc
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                continue  # повторити запит з новим токеном

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", backoff))
                logger.warning("MRKT rate limit (429). Чекаю %.1f сек.", retry_after)
                await asyncio.sleep(retry_after)
                backoff *= 2
                continue

            if resp.status_code >= 500:
                last_error = MrktApiError(f"MRKT server error {resp.status_code}")
                logger.warning("MRKT server error %s (спроба %s)", resp.status_code, attempt + 1)
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if resp.status_code != 200:
                raise MrktApiError(
                    f"MRKT повернув неочікуваний статус {resp.status_code}: {resp.text[:200]}"
                )

            try:
                data = resp.json()
            except ValueError as exc:
                raise MrktApiError(f"MRKT повернув не-JSON відповідь: {exc}") from exc

            self._cache[cache_key] = (time.monotonic(), data)
            return data

        raise MrktApiError(f"Не вдалося виконати запит до MRKT після {retries} спроб: {last_error}")

    async def fetch_gifts_page(
        self,
        *,
        collection_names: Optional[list[str]] = None,
        model_names: Optional[list[str]] = None,
        backdrop_names: Optional[list[str]] = None,
        symbol_names: Optional[list[str]] = None,
        ordering: Optional[str] = "Price",
        low_to_high: bool = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        number: Optional[int] = None,
        cursor: str = "",
        count: int = MAX_PAGE_SIZE,
    ) -> tuple[list[Gift], Optional[str]]:
        body = {
            "collectionNames": collection_names or [],
            "modelNames": model_names or [],
            "backdropNames": backdrop_names or [],
            "symbolNames": symbol_names or [],
            "ordering": ordering,
            "lowToHigh": low_to_high,
            "maxPrice": max_price,
            "minPrice": min_price,
            "mintable": None,
            "number": number,
            "count": min(count, MAX_PAGE_SIZE),
            "cursor": cursor,
            "query": None,
            "promotedFirst": False,
        }
        data = await self._post("/gifts/saling", body)
        raw_gifts = data.get("gifts", [])
        gifts = [Gift.from_api(g) for g in raw_gifts]
        next_cursor = data.get("cursor")
        return gifts, next_cursor

    async def fetch_gifts_all(
        self,
        *,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[Gift]:
        """Проходить пагінацію через cursor до max_pages сторінок або поки cursor не None."""
        all_gifts: list[Gift] = []
        cursor = ""
        for _ in range(max_pages):
            gifts, next_cursor = await self.fetch_gifts_page(cursor=cursor, **filters)
            all_gifts.extend(gifts)
            if not next_cursor:
                break
            cursor = next_cursor
        return all_gifts
