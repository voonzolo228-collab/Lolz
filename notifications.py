import logging

from aiogram import Bot

from mrkt.models import Gift
from services.analyzer import MarketEstimate
from services.scoring import OpportunityResult

logger = logging.getLogger("services.notifications")


def format_opportunity_message(
    gift: Gift,
    estimate: MarketEstimate,
    liquidity_count: int,
    result: OpportunityResult,
) -> str:
    reasons_text = "\n".join(f"• {r}" for r in result.reasons)
    return (
        "🔥 ЗНАЙДЕНО МОЖЛИВУ МОЖЛИВІСТЬ\n\n"
        f"🎁 NFT:\n"
        f"Collection: {gift.collection}\n"
        f"Model: {gift.model or '—'}\n"
        f"Backdrop: {gift.backdrop or '—'}\n"
        f"Symbol: {gift.symbol or '—'}\n"
        f"Number: {gift.number if gift.number is not None else '—'}\n\n"
        f"💰 Поточна ціна:\n{gift.price_ton} TON\n\n"
        f"📈 Орієнтовна ціна перепродажу (медіана {estimate.sample_size} аналогів):\n"
        f"{result.estimated_resale_price} TON\n\n"
        f"💎 Потенційний прибуток (після ~{result.fee_amount} TON комісії):\n"
        f"{result.potential_profit_net} TON\n\n"
        f"🔄 Активних лістингів такого типу:\n{liquidity_count}\n\n"
        f"⭐ Opportunity Score:\n{result.score}/100\n\n"
        f"📊 Чому:\n{reasons_text}\n\n"
        f"🔗 NFT:\n{gift.link or '—'}\n\n"
        f"🛒 Купити:\n{gift.market_url()}"
    )


async def send_opportunity(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)
    except Exception as exc:
        logger.error("Не вдалося надіслати сповіщення до %s: %s", chat_id, exc)
