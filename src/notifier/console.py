from typing import Optional

from src.models import LiquidityInfo, Skin


class ConsoleNotifier:
    def notify(
        self,
        skin: Skin,
        liquidity: LiquidityInfo | None,
        median_brl: Optional[float],
        discount: float,
    ):
        median_tag = f"R${median_brl:.2f}" if median_brl else "N/A"
        discount_tag = f" | desconto: {discount:+.1f}%" if median_brl else ""
        liquid_tag = f" | liquidez: {liquidity.liquidity}/100" if liquidity else ""

        print(
            f"{skin.name} — "
            f"R${skin.price:.2f} | mediana 7d: {median_tag}"
            f"{discount_tag}{liquid_tag} "
            f"| float: {skin.float_value} "
            f"| {skin.url}"
        )
