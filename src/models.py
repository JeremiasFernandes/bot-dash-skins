from dataclasses import dataclass
from datetime import datetime
from typing import Optional


STEAM_CDN = "https://community.akamai.steamstatic.com/economy/image/"


@dataclass
class Skin:
    name: str
    market_hash_name: str
    price: float
    float_value: float
    discount_percent: float
    original_price: float
    url: str
    image_url: str = ""
    available_at: Optional[datetime] = None
    category: Optional[str] = None

    @property
    def savings(self) -> float:
        return self.original_price - self.price


@dataclass
class LiquidityInfo:
    market_hash_name: str
    median_7d: Optional[float]
    liquidity: int  # 0 a 100

    @property
    def is_liquid(self) -> bool:
        return self.liquidity >= 50