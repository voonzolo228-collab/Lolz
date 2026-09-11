from mrkt.models import Gift


def format_gift_line(gift: Gift, extra: str = "") -> str:
    price = f"{gift.price_ton} TON" if gift.price_ton is not None else "ціна невідома"
    number = f"#{gift.number}" if gift.number is not None else ""
    line = f"• {gift.collection} {gift.model or ''} {number} — {price}"
    if extra:
        line += f" ({extra})"
    line += f"\n  {gift.market_url()}"
    return line


def format_gift_list(title: str, gifts: list, extras: dict | None = None) -> str:
    if not gifts:
        return f"{title}\n\nНічого не знайдено за поточними критеріями."
    extras = extras or {}
    lines = [title, ""]
    for g in gifts:
        lines.append(format_gift_line(g, extras.get(g.gift_id, "")))
    return "\n".join(lines)
