"""Scraper de ofertas do Mercado Livre usando Playwright.

O ML bloqueia trafego automatizado redirecionando para /gz/account-verification
(tela "Para continuar, acesse sua conta"). Por isso usamos um perfil de navegador
persistente: rode `python -m bot.login` uma vez, faca login manualmente, e os
cookies ficam salvos para as execucoes seguintes.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from playwright.sync_api import BrowserContext, Page, sync_playwright

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
BLOCK_MARKER = "/gz/account-verification"


class BlockedError(RuntimeError):
    pass


@dataclass
class Promo:
    id: str
    title: str
    url: str
    price: float
    old_price: float | None
    discount: int
    image: str | None
    installments: str | None
    free_shipping: bool


# Extraido no navegador: le cards no layout "poly-card" (atual) com fallback
# para o layout antigo "promotion-item".
EXTRACT_JS = r"""
() => {
  const txt = (el) => (el ? el.textContent.trim() : null);
  const money = (root) => {
    if (!root) return null;
    const frac = root.querySelector('.andes-money-amount__fraction');
    if (!frac) return null;
    const cents = root.querySelector('.andes-money-amount__cents');
    return frac.textContent.replace(/\./g, '') + '.' + (cents ? cents.textContent : '00');
  };
  const cards = document.querySelectorAll('.poly-card, .promotion-item, .andes-card.poly-card');
  const out = [];
  for (const c of cards) {
    const a = c.querySelector('a.poly-component__title, .poly-component__title a, a.promotion-item__link-container, a[href*="mercadolivre.com.br"]');
    if (!a) continue;
    const prev = c.querySelector('s.andes-money-amount--previous, .andes-money-amount--previous');
    const cur = c.querySelector('.poly-price__current .andes-money-amount:not(.andes-money-amount--previous), .andes-money-amount--cents-superscript:not(.andes-money-amount--previous)');
    const disc = c.querySelector('.poly-price__disc_label, .andes-money-amount__discount, .promotion-item__discount-text');
    const img = c.querySelector('img.poly-component__picture, img');
    out.push({
      title: txt(a) || txt(c.querySelector('.promotion-item__title')),
      url: a.href,
      price: money(cur),
      old_price: money(prev),
      discount: txt(disc),
      image: img ? (img.getAttribute('data-src') || img.src) : null,
      installments: txt(c.querySelector('.poly-price__installments')),
      shipping: txt(c.querySelector('.poly-component__shipping')),
    });
  }
  return out;
}
"""

ITEM_ID_RE = re.compile(r"(MLB-?\d+)", re.I)


def _item_id(url: str) -> str:
    m = ITEM_ID_RE.search(url)
    return m.group(1).replace("-", "").upper() if m else urlparse(url).path


def _clean_url(url: str, affiliate_params: str) -> str:
    """Remove tracking do ML (#hash e query) e aplica parametros de afiliado."""
    parts = urlparse(url)
    query = urlencode(parse_qsl(affiliate_params)) if affiliate_params else ""
    return urlunparse((parts.scheme, parts.netloc, parts.path, "", query, ""))


def _to_promo(raw: dict, affiliate_params: str) -> Promo | None:
    if not raw.get("title") or not raw.get("url") or not raw.get("price"):
        return None
    price = float(raw["price"])
    old_price = float(raw["old_price"]) if raw.get("old_price") else None
    discount = 0
    if raw.get("discount"):
        m = re.search(r"(\d+)\s*%", raw["discount"])
        discount = int(m.group(1)) if m else 0
    if not discount and old_price and old_price > price:
        discount = round((1 - price / old_price) * 100)
    image = raw.get("image")
    if image and image.startswith("data:"):
        image = None
    return Promo(
        id=_item_id(raw["url"]),
        title=raw["title"],
        url=_clean_url(raw["url"], affiliate_params),
        price=price,
        old_price=old_price,
        discount=discount,
        image=image,
        installments=raw.get("installments"),
        free_shipping="grátis" in (raw.get("shipping") or "").lower(),
    )


def open_context(p, profile_dir: Path, headless: bool) -> BrowserContext:
    profile_dir.mkdir(parents=True, exist_ok=True)
    ctx = p.chromium.launch_persistent_context(
        str(profile_dir),
        headless=headless,
        locale="pt-BR",
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return ctx


def _page_url(base: str, page_num: int) -> str:
    if page_num == 1:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}page={page_num}"


def _scroll(page: Page) -> None:
    # Imagens e alguns cards carregam sob demanda
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(700)


def scrape(urls: list[str], max_pages: int, profile_dir: Path, headless: bool,
           affiliate_params: str = "", debug_dir: Path | None = None) -> list[Promo]:
    promos: dict[str, Promo] = {}
    with sync_playwright() as p:
        ctx = open_context(p, profile_dir, headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for u_idx, base in enumerate(urls):
                for n in range(1, max_pages + 1):
                    url = _page_url(base, n)
                    log.info("Abrindo %s", url)
                    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    page.wait_for_timeout(2500)
                    if BLOCK_MARKER in page.url:
                        raise BlockedError(
                            "Mercado Livre pediu login/verificacao. Rode `python -m bot.login` "
                            "e faca login no navegador que abrir."
                        )
                    _scroll(page)
                    raw_items = page.evaluate(EXTRACT_JS)
                    if debug_dir:
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        (debug_dir / f"url{u_idx}_page{n}.html").write_text(page.content(), encoding="utf-8")
                    found = [x for x in (_to_promo(r, affiliate_params) for r in raw_items) if x]
                    log.info("  %d cards, %d validos", len(raw_items), len(found))
                    if not found:
                        break
                    for promo in found:
                        promos.setdefault(promo.id, promo)
        finally:
            ctx.close()
    return list(promos.values())
