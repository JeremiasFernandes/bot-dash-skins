from datetime import datetime, timezone

from src.config import MIN_DISCOUNT_PERCENT
from src.models import Skin

_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def filter_by_discount(skins: list[Skin], min_discount: float = MIN_DISCOUNT_PERCENT) -> list[Skin]:
    return [s for s in skins if s.discount_percent >= min_discount]


def sort_by_available_at(skins: list[Skin]) -> list[Skin]:
    return sorted(skins, key=lambda s: s.available_at or _EPOCH, reverse=True)


def sort_by_discount(skins: list[Skin], descending: bool = True) -> list[Skin]:
    return sorted(skins, key=lambda s: s.discount_percent, reverse=descending)