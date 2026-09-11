"""
Моделі даних MRKT gift, побудовані на РЕАЛЬНІЙ структурі відповіді
/api/v1/gifts/saling (задокументовано в boostNT/MRKT-API та tgmrkt-api).

Поля позначені як Optional там, де MRKT може їх не повертати —
у такому разі код НЕ повинен вигадувати значення, а явно відображати
"немає даних".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Gift:
    raw: dict[str, Any] = field(repr=False)

    gift_id: str
    collection: str
    model: Optional[str]
    backdrop: Optional[str]
    symbol: Optional[str]
    number: Optional[int]
    price_ton: Optional[float]
    mintable: Optional[bool]
    link: Optional[str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Gift":
        # MRKT повертає ціну в nanoTON в деяких відповідях, в інших - вже в TON.
        # Тут беремо значення як є з поля "price"/"priceTon", без домислювання
        # курсів чи одиниць, яких немає в самій відповіді.
        gift_id = str(
            data.get("id")
            or data.get("giftId")
            or data.get("nftId")
            or data.get("slug")
            or ""
        )
        price = data.get("price")
        if price is None:
            price = data.get("priceTon")

        collection = data.get("collectionName") or data.get("collection") or "Unknown"
        model = data.get("modelName") or data.get("model")
        backdrop = data.get("backdropName") or data.get("backdrop")
        symbol = data.get("symbolName") or data.get("symbol")
        number = data.get("number")
        mintable = data.get("mintable")

        link = None
        slug = data.get("slug") or data.get("name")
        if slug:
            link = f"https://t.me/nft/{slug}"

        return cls(
            raw=data,
            gift_id=gift_id,
            collection=collection,
            model=model,
            backdrop=backdrop,
            symbol=symbol,
            number=int(number) if number is not None else None,
            price_ton=float(price) if price is not None else None,
            mintable=mintable,
            link=link,
        )

    def market_url(self) -> str:
        return f"https://t.me/mrkt/app?startapp=gift_{self.gift_id}"

    def identity_key(self) -> str:
        """Ключ для групування 'аналогічних' NFT: та сама колекція+модель+backdrop+symbol."""
        return f"{self.collection}|{self.model}|{self.backdrop}|{self.symbol}"
