import json
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from src.config import ANALYSIS_RESULTS_PATH
from src.pipeline import analyze, refresh_caches

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

st.set_page_config(page_title="Bot Skins", page_icon="🔫", layout="wide")

CARD_CSS = """
<style>
.skin-card {
    border: 1px solid #333;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    background: #1a1a2e;
    transition: transform 0.15s, box-shadow 0.15s;
    text-decoration: none;
    color: inherit;
    display: flex;
    align-items: center;
    gap: 1.2rem;
}
.skin-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    border-color: #5865f2;
}
.skin-card img {
    width: 160px;
    height: 120px;
    object-fit: contain;
    border-radius: 8px;
    background: #0f0f1a;
    flex-shrink: 0;
}
.skin-card .info {
    flex: 1;
    min-width: 0;
}
.skin-card .name {
    font-weight: 600;
    font-size: 1rem;
    margin: 0 0 0.25rem;
    color: #e0e0e0;
}
.skin-card .price {
    font-size: 1.3rem;
    font-weight: 700;
    color: #43b581;
}
.skin-card .meta {
    font-size: 0.85rem;
    color: #999;
    margin-top: 0.25rem;
}
.skin-card .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 0.4rem;
}
.badge-green { background: #1a3a2a; color: #43b581; }
.badge-yellow { background: #3a3a1a; color: #faa61a; }
.badge-red { background: #3a1a1a; color: #f04747; }
</style>
"""


def _load_results() -> dict | None:
    if not ANALYSIS_RESULTS_PATH.exists():
        return None
    with open(ANALYSIS_RESULTS_PATH) as f:
        return json.load(f)


def _discount_badge(discount: float | None) -> str:
    if discount is None:
        return ""
    if discount > 0:
        cls = "badge-green"
    elif discount > -20:
        cls = "badge-yellow"
    else:
        cls = "badge-red"
    return f'<span class="badge {cls}">{discount:+.1f}%</span>'


def _liquidity_text(liq: int | None) -> str:
    if liq is None:
        return "N/A"
    return f"{liq}/100"


def _render_card(skin: dict) -> str:
    img = skin.get("image_url") or ""
    img_tag = f'<img src="{img}" alt="{skin["name"]}">' if img else ""
    median_txt = f'R${skin["median_brl"]:.2f}' if skin.get("median_brl") else "N/A"
    badge = _discount_badge(skin.get("median_discount"))

    return f"""
    <a class="skin-card" href="{skin['url']}" target="_blank" rel="noopener">
        {img_tag}
        <div class="info">
            <div class="name">{skin['name']}</div>
            <div class="price">R${skin['price']:.2f}</div>
            <div class="meta">
                Mediana 7d: {median_txt} &middot;
                Float: {skin['float_value']:.4f} &middot;
                Liquidez: {_liquidity_text(skin.get('liquidity'))}
            </div>
            {badge}
        </div>
    </a>
    """


def _run_analysis():
    refresh_caches()
    analyze(collection_window=0)


st.markdown(CARD_CSS, unsafe_allow_html=True)

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("Bot Skins Dashboard")
with col_btn:
    st.write("")
    if st.button("Rodar Agora", type="primary", use_container_width=True):
        with st.spinner("Coletando e analisando skins..."):
            _run_analysis()
        st.rerun()

data = _load_results()

if not data:
    st.info("Nenhuma análise encontrada. Clique em **Rodar Agora** para iniciar.")
    st.stop()

analyzed_at = datetime.fromisoformat(data["analyzed_at"])
age_min = (datetime.now(timezone.utc) - analyzed_at).total_seconds() / 60
st.caption(f"Última análise: {analyzed_at:%d/%m/%Y %H:%M UTC} ({age_min:.0f} min atrás) · {data['total']} skins")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    category_opts = sorted({s["category"] for s in data["skins"] if s.get("category")})
    selected_cat = st.multiselect("Categoria", category_opts)
with col_f2:
    min_liq = st.slider("Liquidez mínima", 0, 100, 0)
with col_f3:
    sort_opt = st.selectbox("Ordenar por", ["Desconto (mediana)", "Preço", "Liquidez", "Float"])

skins = data["skins"]
if selected_cat:
    skins = [s for s in skins if s.get("category") in selected_cat]
if min_liq > 0:
    skins = [s for s in skins if (s.get("liquidity") or 0) >= min_liq]

if sort_opt == "Preço":
    skins.sort(key=lambda s: s["price"])
elif sort_opt == "Liquidez":
    skins.sort(key=lambda s: s.get("liquidity") or 0, reverse=True)
elif sort_opt == "Float":
    skins.sort(key=lambda s: s["float_value"])

if not skins:
    st.warning("Nenhuma skin encontrada com os filtros selecionados.")
    st.stop()

st.markdown(f"**{len(skins)}** skins")

for skin in skins:
    st.markdown(_render_card(skin), unsafe_allow_html=True)
