import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from src.config import (
    LIQUIDITY_CACHE_PATH,
    REQUEST_TIMEOUT,
    SKINSTRACK_API_URL,
)
from src.models import LiquidityInfo

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 24 * 60 * 60


class LiquidityCache:
    def __init__(self, path: Path = LIQUIDITY_CACHE_PATH):
        self._path = path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if not self._path.exists():
            logger.info("[LIQUIDEZ] Arquivo de cache não encontrado, iniciando vazio.")
            return
        try:
            with open(self._path) as f:
                self._data = json.load(f)
            any_entry = next(iter(self._data.values()), {})
            age = (time.time() - any_entry.get("fetched_at", 0)) / 3600
            logger.info("[LIQUIDEZ] Cache carregado do disco: %d itens (idade: %.1fh).", len(self._data), age)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("[LIQUIDEZ] Erro ao carregar cache: %s", e)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        logger.info("[LIQUIDEZ] Cache salvo em %s.", self._path)

    def is_stale(self) -> bool:
        if not self._data:
            return True
        any_entry = next(iter(self._data.values()), {})
        return time.time() - any_entry.get("fetched_at", 0) > CACHE_TTL_SECONDS

    def get(self, market_hash_name: str) -> Optional[LiquidityInfo]:
        entry = self._data.get(market_hash_name)
        if not entry:
            return None
        return LiquidityInfo(
            market_hash_name=market_hash_name,
            median_7d=entry.get("median_7d"),
            liquidity=entry.get("liquidity", 0),
        )

    def populate(self):
        api_key = os.environ.get("SKINSTRACK_API_KEY")
        if not api_key:
            logger.warning("[LIQUIDEZ] SKINSTRACK_API_KEY não definida. Pulando atualização.")
            return

        logger.info("[LIQUIDEZ] Descartando cache anterior (%d itens). Consultando SkinsTrack API (/paid/items)...", len(self._data))

        try:
            t0 = time.time()
            resp = httpx.get(
                f"{SKINSTRACK_API_URL}/paid/items",
                params={"median": "true"},
                headers={"X-API-KEY": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json()
            elapsed = time.time() - t0
            logger.info("[LIQUIDEZ] API respondeu em %.1fs com %d itens.", elapsed, len(items))
        except httpx.HTTPError as e:
            logger.error("[LIQUIDEZ] Falha na consulta à SkinsTrack: %s", e)
            return

        now = time.time()
        self._data = {}
        with_median = 0
        for item in items:
            mhn = item.get("market_hash_name", "")
            if not mhn:
                continue
            median_obj = item.get("median") or {}
            median_7d = median_obj.get("7d")
            if median_7d is not None:
                with_median += 1
            self._data[mhn] = {
                "median_7d": median_7d,
                "liquidity": item.get("liquidity", 0),
                "fetched_at": now,
            }

        self._save()
        logger.info(
            "[LIQUIDEZ] Cache atualizado: %d itens totais, %d com mediana 7d.",
            len(self._data), with_median,
        )
