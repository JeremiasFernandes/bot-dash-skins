import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from src.config import EXCHANGE_RATE_CACHE_PATH

logger = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/7"
CACHE_TTL_SECONDS = 24 * 60 * 60


class ExchangeRateCache:
    def __init__(self, path: Path = EXCHANGE_RATE_CACHE_PATH):
        self._path = path
        self._rate: Optional[float] = None
        self._fetched_at: float = 0
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            self._rate = data.get("rate")
            self._fetched_at = data.get("fetched_at", 0)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Erro ao carregar cache de câmbio: %s", e)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"rate": self._rate, "fetched_at": self._fetched_at}, f)

    def get_rate(self) -> Optional[float]:
        return self._rate

    def populate(self):
        if self._rate and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            logger.info("Cache de câmbio ainda válido (USD/BRL = %.4f).", self._rate)
            return

        logger.info("Consultando cotação USD/BRL no Banco Central...")

        try:
            resp = httpx.get(BCB_SGS_URL, params={"formato": "json"}, timeout=15)
            resp.raise_for_status()
            entries = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error("Erro ao consultar BCB: %s", e)
            return

        values = [float(e["valor"]) for e in entries if e.get("valor")]
        if not values:
            logger.error("Nenhuma cotação retornada pelo BCB.")
            return

        self._rate = sum(values) / len(values)
        self._fetched_at = time.time()
        self._save()

        logger.info(
            "Câmbio atualizado: média 7d USD/BRL = %.4f (%d cotações).",
            self._rate, len(values),
        )
