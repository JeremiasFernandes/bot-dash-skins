import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Optional

from curl_cffi.requests import Session

from src.config import BASE_URL, REQUEST_HEADERS, REQUEST_TIMEOUT
from src.models import STEAM_CDN, Skin

logger = logging.getLogger(__name__)

API_LISTING = f"{BASE_URL}/api/listing"


def _build_client() -> Session:
    return Session(
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
        impersonate="chrome136",
    )


def _fetch_page(
    client: Session,
    cursor: Optional[str] = None,
    limit: int = 50,
) -> Optional[dict]:
    params = {
        "sort_by": "date",
        "limit": str(limit),
        "price_min": 50,
        "price_max": 3000,
    }
    if cursor:
        params["cursor"] = cursor

    try:
        resp = client.get(API_LISTING, params=params, allow_redirects=True)
        if resp.status_code != 200:
            logger.error(
                "API retornou HTTP %d. URL: %s | Headers resposta: %s | Body (500 chars): %.500s",
                resp.status_code,
                resp.url,
                dict(resp.headers),
                resp.text,
            )
            resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Falha ao acessar API: %s", e)
        return None


def _slugify(market_hash_name: str) -> str:
    s = market_hash_name.replace("™", "").replace("★", "")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


EXCLUDED_PATTERNS = re.compile(r"Doppler|Fade|Case Hardened", re.IGNORECASE)
WEAPON_TYPES = {"Pistola", "Rifle", "Rifle de Precisão", "Submetralhadora", "Faca", "Luvas"}


def _is_excluded(item: dict) -> bool:
    if item.get("item_type") not in WEAPON_TYPES:
        return True
    return bool(EXCLUDED_PATTERNS.search(item.get("market_hash_name", "")))


def _parse_available_at(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _parse_item(item: dict) -> Optional[Skin]:
    try:
        wear_data = item.get("wear_data") or {}
        float_value = wear_data.get("floatvalue", 0.0)
        slug = _slugify(item["market_hash_name"])
        available_at = _parse_available_at(item.get("availableAt"))

        image_url = wear_data.get("image", "")
        if not image_url and item.get("icon_url"):
            image_url = f"{STEAM_CDN}{item['icon_url']}"

        return Skin(
            name=item["name"],
            market_hash_name=item["market_hash_name"],
            price=item["price"],
            float_value=float_value,
            discount_percent=item.get("discount", 0),
            original_price=item.get("steamPrice", 0.0),
            url=f"{BASE_URL}/item/{slug}/{item['_id']}",
            image_url=image_url,
            available_at=available_at,
            category=item.get("weapon"),
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("Erro ao parsear item: %s", e)
        return None


def fetch_skins() -> list[Skin]:
    today = datetime.now(timezone.utc).date()
    skins: list[Skin] = []
    cursor = None
    hit_previous_day = False

    with _build_client() as client:
        while not hit_previous_day:
            data = _fetch_page(client, cursor=cursor)
            if not data:
                break

            for item in data.get("results", []):
                available_at = _parse_available_at(item.get("availableAt"))
                if available_at and available_at.date() < today:
                    hit_previous_day = True
                    break

                if _is_excluded(item):
                    continue
                skin = _parse_item(item)
                if skin and skin.float_value >= 0:
                    skins.append(skin)

            if hit_previous_day or not data.get("hasMore"):
                break
            cursor = data.get("nextCursor")

            time.sleep(random.uniform(1.0, 3.0))

    logger.info("%d skins listadas hoje (%s).", len(skins), today.isoformat())
    return skins
