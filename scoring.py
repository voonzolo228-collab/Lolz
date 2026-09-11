"""
Opportunity Score (0-100): зважена формула з поясненими компонентами.
Не випадкова, не "магічна" - кожна вага задокументована нижче.

Компоненти (сума ваг = 100):
- price_gap   (40): наскільки поточна ціна нижча за медіанну оцінку ринку.
                     0%, якщо ціна >= ринкової. 100% ваги компонента,
                     якщо ціна на 50%+ нижча за ринкову (капується).
- liquidity   (20): кількість активних лістингів того ж collection+model
                     як проксі попиту/ліквідності (більше лістингів
                     такого типу історично означає легше перепродати,
                     до розумної межі, після якої це вже надлишок пропозиції).
- sample_conf (20): наскільки надійна вибірка для оцінки ринкової ціни
                     (exact_match > same_collection_model > same_collection,
                     і чим більше зразків, тим вища довіра).
- rarity_number (10): бонус за "красивий"/рідкісний номер NFT
                       (див. utils.number_beauty).
- profit_after_fees (10): чи лишається прибуток додатним після
                           комісії маркету (фіксована ставка з конфігу).
"""
from dataclasses import dataclass
from typing import Optional

from services.analyzer import MarketEstimate

MRKT_FEE_RATE = 0.05  # 5% - типова комісія торгових майданчиків NFT-подарунків;
# ЯКЩО фактична комісія MRKT відрізняється, зміни це значення -
# бот не повинен видавати вигадану ставку як підтверджений факт.

SCOPE_CONFIDENCE = {
    "exact_match": 1.0,
    "same_collection_model": 0.7,
    "same_collection": 0.4,
}


@dataclass
class OpportunityResult:
    score: int
    estimated_resale_price: float
    potential_profit_gross: float
    potential_profit_net: float
    fee_amount: float
    reasons: list[str]


def compute_opportunity(
    purchase_price: float,
    estimate: MarketEstimate,
    liquidity_count: int,
    number_beauty_score: int,
) -> Optional[OpportunityResult]:
    if estimate.median_price is None or estimate.median_price <= 0:
        return None

    resale_price = estimate.median_price
    fee_amount = resale_price * MRKT_FEE_RATE
    profit_gross = resale_price - purchase_price
    profit_net = profit_gross - fee_amount

    reasons: list[str] = []

    # price_gap (0-40)
    if purchase_price >= resale_price:
        price_gap_score = 0.0
    else:
        gap_ratio = (resale_price - purchase_price) / resale_price
        price_gap_score = min(gap_ratio / 0.5, 1.0) * 40
        reasons.append(f"ціна на {gap_ratio * 100:.0f}% нижча за медіану аналогів")

    # liquidity (0-20) - насичення після ~15 активних лістингів того ж типу
    liquidity_score = min(liquidity_count / 15, 1.0) * 20
    if liquidity_count > 0:
        reasons.append(f"{liquidity_count} активних лістингів такого ж типу")

    # sample_conf (0-20)
    scope_weight = SCOPE_CONFIDENCE.get(estimate.comparison_scope, 0.2)
    sample_size_weight = min(estimate.sample_size / 10, 1.0)
    sample_conf_score = scope_weight * sample_size_weight * 20
    reasons.append(
        f"оцінка ринку базується на {estimate.sample_size} аналогах ({estimate.comparison_scope})"
    )

    # rarity_number (0-10)
    rarity_score = (number_beauty_score / 100) * 10
    if number_beauty_score > 0:
        reasons.append(f"бонус за номер (beauty score {number_beauty_score}/100)")

    # profit_after_fees (0-10)
    if profit_net <= 0:
        profit_score = 0.0
    else:
        profit_score = min(profit_net / (purchase_price * 0.3 + 1e-9), 1.0) * 10
        reasons.append(f"чистий прибуток після комісії ~{profit_net:.2f} TON")

    total = price_gap_score + liquidity_score + sample_conf_score + rarity_score + profit_score

    return OpportunityResult(
        score=round(min(total, 100)),
        estimated_resale_price=round(resale_price, 3),
        potential_profit_gross=round(profit_gross, 3),
        potential_profit_net=round(profit_net, 3),
        fee_amount=round(fee_amount, 3),
        reasons=reasons,
    )
