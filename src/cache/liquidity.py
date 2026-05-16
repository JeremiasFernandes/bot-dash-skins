import json
import logging
import os
import time
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
            logger.info("Cache de liquidez não encontrado em %s, iniciando vazio.", self._path)
            return
        try:
            with open(self._path) as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Erro ao carregar cache de liquidez: %s", e)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

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
            logger.warning("SKINSTRACK_API_KEY não definida, pulando consulta de liquidez.")
            return

        if not self.is_stale():
            logger.info("Cache de liquidez ainda válido (%d itens).", len(self._data))
            return

        logger.info("Baixando cache completo de liquidez da SkinsTrack...")

        try:
            resp = httpx.get(
                f"{SKINSTRACK_API_URL}/paid/items",
                params={"median": "true"},
                headers={"X-API-KEY": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json()
        except httpx.HTTPError as e:
            logger.error("Erro ao consultar SkinsTrack: %s", e)
            return

        now = time.time()
        self._data = {}
        for item in items:
            mhn = item.get("market_hash_name", "")
            if not mhn:
                continue
            median_obj = item.get("median") or {}
            self._data[mhn] = {
                "median_7d": median_obj.get("7d"),
                "liquidity": item.get("liquidity", 0),
                "fetched_at": now,
            }

        self._save()
        logger.info("Cache de liquidez atualizado: %d itens.", len(self._data))
