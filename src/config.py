from pathlib import Path

BASE_URL = "https://dashskins.com.br"

LIQUIDITY_CACHE_PATH = Path(__file__).parent.parent / "data" / "liquidity_cache.json"
EXCHANGE_RATE_CACHE_PATH = Path(__file__).parent.parent / "data" / "exchange_rate.json"

TIMEZONE = "America/Sao_Paulo"

REQUEST_TIMEOUT = 30
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://dashskins.com.br/",
    "Origin": "https://dashskins.com.br",
    "Sec-Ch-Ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Connection": "keep-alive",
}

SKINSTRACK_API_URL = "https://api.skinstrack.com/v2"
