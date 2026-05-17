import json
import logging
import time
from datetime import datetime
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
            logger.info("[CÂMBIO] Arquivo de cache não encontrado, iniciando vazio.")
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            self._rate = data.get("rate")
            self._fetched_at = data.get("fetched_at", 0)
            age = (time.time() - self._fetched_at) / 3600
            logger.info("[CÂMBIO] Cache carregado do disco: USD/BRL = %.4f (idade: %.1fh).", self._rate, age)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("[CÂMBIO] Erro ao carregar cache: %s", e)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"rate": self._rate, "fetched_at": self._fetched_at}, f)
        logger.info("[CÂMBIO] Cache salvo em %s.", self._path)

    def get_rate(self) -> Optional[float]:
        return self._rate

    def populate(self):
        if self._rate and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            remaining = CACHE_TTL_SECONDS - (time.time() - self._fetched_at)
            logger.info("[CÂMBIO] Cache ainda válido (USD/BRL = %.4f). Expira em %.1fh.", self._rate, remaining / 3600)
            return

        logger.info("[CÂMBIO] Cache expirado ou vazio. Consultando API do Banco Central (série SGS 1)...")

        try:
            resp = httpx.get(BCB_SGS_URL, params={"formato": "json"}, timeout=15)
            resp.raise_for_status()
            entries = resp.json()
            logger.info("[CÂMBIO] API respondeu com %d cotações.", len(entries))
        except (httpx.HTTPError, ValueError) as e:
            logger.error("[CÂMBIO] Falha na consulta ao BCB: %s", e)
            return

        values = [float(e["valor"]) for e in entries if e.get("valor")]
        if not values:
            logger.error("[CÂMBIO] API retornou 0 cotações válidas.")
            return

        for e in entries:
            logger.info("[CÂMBIO]   %s -> R$ %s", e.get("data"), e.get("valor"))

        self._rate = sum(values) / len(values)
        self._fetched_at = time.time()
        self._save()

        logger.info("[CÂMBIO] Média 7d calculada: USD/BRL = %.4f (%d cotações).", self._rate, len(values))
