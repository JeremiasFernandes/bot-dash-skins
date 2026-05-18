import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from src.cache import ExchangeRateCache, LiquidityCache
from src.config import ANALYSIS_RESULTS_PATH
from src.notifier import ConsoleNotifier
from src.scraper import fetch_skins

logger = logging.getLogger(__name__)

COLLECTION_WINDOW_SECONDS = 5 * 60
RETRY_INTERVAL_SECONDS = 30


def _median_discount(price: float, median_brl: Optional[float]) -> float:
    if not median_brl:
        return 0.0
    return (1 - price / median_brl) * 100


def _save_results(results: list[dict]):
    ANALYSIS_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "skins": results,
    }
    with open(ANALYSIS_RESULTS_PATH, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Resultados salvos em %s (%d skins).", ANALYSIS_RESULTS_PATH, len(results))


def refresh_caches():
    logger.info("Atualizando caches...")

    exchange = ExchangeRateCache()
    exchange.populate()

    cache = LiquidityCache()
    cache.populate()

    logger.info("Caches atualizados.")


def _collect_skins(window_seconds: int) -> list:
    collected: dict[str, object] = {}
    deadline = time.time() + window_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            skins = fetch_skins()
            new = 0
            for s in skins:
                if s.url not in collected:
                    collected[s.url] = s
                    new += 1
            logger.info(
                "Coleta #%d: %d skins obtidas, %d novas. Total acumulado: %d.",
                attempt, len(skins), new, len(collected),
            )
        except Exception:
            logger.exception("Erro na coleta #%d.", attempt)

        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(RETRY_INTERVAL_SECONDS, remaining))

    logger.info(
        "Janela de coleta encerrada. %d skins únicas em %d tentativas.",
        len(collected), attempt,
    )
    return list(collected.values())


def analyze(collection_window: int = COLLECTION_WINDOW_SECONDS):
    logger.info("Iniciando análise de skins (janela de coleta: %ds)...", collection_window)

    exchange = ExchangeRateCache()
    usd_brl = exchange.get_rate()
    if not usd_brl:
        logger.error("Câmbio USD/BRL não disponível. Execute refresh_caches primeiro.")
        return

    cache = LiquidityCache()

    skins = _collect_skins(collection_window)
    if not skins:
        logger.warning("Nenhuma skin encontrada após janela de coleta.")
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
    results = []

    for skin in ranked:
        liquidity = cache.get(skin.market_hash_name)
        med_brl = median_brl(skin.market_hash_name)
        discount = _median_discount(skin.price, med_brl)
        notifier.notify(skin, liquidity, med_brl, discount)
        results.append({
            "name": skin.name,
            "market_hash_name": skin.market_hash_name,
            "price": skin.price,
            "float_value": skin.float_value,
            "discount_percent": skin.discount_percent,
            "original_price": skin.original_price,
            "url": skin.url,
            "image_url": skin.image_url,
            "category": skin.category,
            "median_brl": med_brl,
            "median_discount": discount,
            "liquidity": liquidity.liquidity if liquidity else None,
        })

    _save_results(results)
