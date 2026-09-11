"""
ОБМЕЖЕННЯ ДАНИХ: /gifts/saling дає лише ПОТОЧНІ активні лістинги,
без історії продажів (немає підтвердженого endpoint для sales
history). Тому "Estimated Resale Price" тут будується на статистиці
поточних лістингів максимально схожих NFT (та сама collection +
model + backdrop + symbol, якщо можливо; з поступовим розширенням
групи, якщо точних аналогів замало) - це проксі ринкової ціни,
а не факт історичних продажів. Якщо аналогів замало - функція чесно
повертає None замість вигаданого числа.
"""
import statistics
from dataclasses import dataclass
from typing import Optional

from mrkt.models import Gift

MIN_SAMPLE_FOR_ESTIMATE = 3


@dataclass
class MarketEstimate:
    sample_size: int
    median_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    comparison_scope: str  # "exact_match" | "same_collection_model" | "same_collection"


def group_by_identity(gifts: list[Gift]) -> dict[str, list[Gift]]:
    groups: dict[str, list[Gift]] = {}
    for g in gifts:
        groups.setdefault(g.identity_key(), []).append(g)
    return groups


def estimate_market_price(target: Gift, universe: list[Gift]) -> Optional[MarketEstimate]:
    """
    Шукає найближчих аналогів target серед universe (усі активні лістинги,
    отримані під час поточного циклу моніторингу), звужуючи/розширюючи
    критерій відповідності залежно від наявної кількості даних.
    """
    priced = [g for g in universe if g.price_ton is not None and g.gift_id != target.gift_id]

    def collect(predicate) -> list[float]:
        return [g.price_ton for g in priced if predicate(g)]

    # 1. Точний збіг: collection + model + backdrop + symbol
    exact = collect(
        lambda g: g.collection == target.collection
        and g.model == target.model
        and g.backdrop == target.backdrop
        and g.symbol == target.symbol
    )
    if len(exact) >= MIN_SAMPLE_FOR_ESTIMATE:
        return _build_estimate(exact, "exact_match")

    # 2. collection + model
    same_model = collect(
        lambda g: g.collection == target.collection and g.model == target.model
    )
    if len(same_model) >= MIN_SAMPLE_FOR_ESTIMATE:
        return _build_estimate(same_model, "same_collection_model")

    # 3. вся колекція
    same_collection = collect(lambda g: g.collection == target.collection)
    if len(same_collection) >= MIN_SAMPLE_FOR_ESTIMATE:
        return _build_estimate(same_collection, "same_collection")

    return None  # недостатньо даних - краще нічого не показати, ніж вигадати


def _build_estimate(prices: list[float], scope: str) -> MarketEstimate:
    return MarketEstimate(
        sample_size=len(prices),
        median_price=statistics.median(prices),
        min_price=min(prices),
        max_price=max(prices),
        comparison_scope=scope,
    )


def liquidity_proxy(target: Gift, universe: list[Gift]) -> int:
    """
    'Оборот' у класичному сенсі (обсяг продажів за період) MRKT API
    не надає. Замість вигадування цифри використовуємо ЧЕСНИЙ проксі:
    кількість активних лістингів у тій самій collection+model - це
    показник пропозиції/популярності, а не факту продажів.
    Позначається в UI явно як 'активних лістингів', не 'оборот'.
    """
    return sum(
        1
        for g in universe
        if g.collection == target.collection and g.model == target.model
    )
