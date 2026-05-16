import logging
from typing import Optional

from src.cache import ExchangeRateCache, LiquidityCache
from src.notifier import ConsoleNotifier
from src.scraper import fetch_skins

logger = logging.getLogger(__name__)


def _median_discount(price: float, median_brl: Optional[float]) -> float:
    if not median_brl:
        return 0.0
    return (1 - price / median_brl) * 100


def refresh_caches():
    logger.info("Atualizando caches...")

    exchange = ExchangeRateCache()
    exchange.populate()

    cache = LiquidityCache()
    cache.populate()

    logger.info("Caches atualizados.")


def analyze():
    logger.info("Iniciando análise de skins...")

    exchange = ExchangeRateCache()
    usd_brl = exchange.get_rate()
    if not usd_brl:
        logger.error("Câmbio USD/BRL não disponível. Execute refresh_caches primeiro.")
        return

    cache = LiquidityCache()

    skins = fetch_skins()
    if not skins:
        logger.warning("Nenhuma skin encontrada no scraping.")
        return

    def median_brl(market_hash_name: str) -> Optional[float]:
        info = cache.get(market_hash_name)
        if not info or not info.median_7d or not usd_brl:
            return None
        return info.median_7d * usd_brl

    ranked = sorted(
        skins,
        key=lambda s: _median_discount(s.price, median_brl(s.market_hash_name)),
        reverse=True,
    )

    notifier = ConsoleNotifier()

    for skin in ranked:
        liquidity = cache.get(skin.market_hash_name)
        med_brl = median_brl(skin.market_hash_name)
        discount = _median_discount(skin.price, med_brl)
        notifier.notify(skin, liquidity, med_brl, discount)
