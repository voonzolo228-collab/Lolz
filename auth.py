"""
Отримання MRKT auth-токена через Telegram Mini App init_data.

Підтверджений реальний потік (boostNT/MRKT-API):
1. Через Pyrogram-клієнт (твій особистий api_id/api_hash) робимо
   RequestAppWebView до бота @mrkt.
2. З URL відповіді дістаємо tgWebAppData -> init_data.
3. POST https://api.tgmrkt.io/api/v1/auth з {"data": init_data} -> token.

Токен не хардкодиться і не пишеться в логи. При 401 з API токен
автоматично перевидається (див. MrktClient._ensure_token).
"""
import logging
import time
from urllib.parse import unquote

import httpx
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName, InputUser

logger = logging.getLogger("mrkt.auth")


class MrktAuthError(RuntimeError):
    pass


class MrktAuth:
    def __init__(self, pyrogram_client: Client, api_base: str, mrkt_bot_username: str):
        self._client = pyrogram_client
        self._api_base = api_base.rstrip("/")
        self._mrkt_bot_username = mrkt_bot_username
        self._token: str | None = None
        self._token_obtained_at: float = 0.0

    @property
    def token(self) -> str | None:
        return self._token

    async def _get_init_data(self) -> str:
        """Викликає RequestAppWebView через власний Telegram user client."""
        bot_entity = await self._client.get_users(self._mrkt_bot_username)
        peer = await self._client.resolve_peer(self._mrkt_bot_username)

        bot = InputUser(user_id=bot_entity.id, access_hash=bot_entity.raw.access_hash)
        bot_app = InputBotAppShortName(bot_id=bot, short_name="app")

        web_view = await self._client.invoke(
            RequestAppWebView(
                peer=peer,
                app=bot_app,
                platform="android",
            )
        )

        url = web_view.url
        if "tgWebAppData=" not in url:
            raise MrktAuthError(
                "Не вдалося отримати tgWebAppData з відповіді Telegram Mini App. "
                "Можливо, MRKT змінив short_name застосунку або платформу запиту."
            )
        init_data = unquote(url.split("tgWebAppData=", 1)[1].split("&tgWebAppVersion", 1)[0])
        return init_data

    async def refresh_token(self) -> str:
        """Повністю проходить flow і оновлює self._token. Секрет у логи не пишеться."""
        init_data = await self._get_init_data()

        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                f"{self._api_base}/auth",
                json={"data": init_data},
            )
        if resp.status_code != 200:
            raise MrktAuthError(
                f"MRKT /auth повернув статус {resp.status_code}. "
                f"Тіло відповіді: {resp.text[:200]}"
            )
        payload = resp.json()
        token = payload.get("token")
        if not token:
            raise MrktAuthError("MRKT /auth не повернув поле 'token' у відповіді.")

        self._token = token
        self._token_obtained_at = time.monotonic()
        logger.info("MRKT auth token успішно оновлено (значення приховано в логах).")
        return token

    def token_age_seconds(self) -> float:
        if not self._token:
            return float("inf")
        return time.monotonic() - self._token_obtained_at
