"""Abre o navegador com o perfil persistente para login manual no Mercado Livre.

Uso: python -m bot.login
Faca login, confirme que /ofertas carrega os produtos e feche a janela.
"""
from playwright.sync_api import sync_playwright

from .config import load_config
from .scraper import open_context


def main() -> None:
    cfg = load_config()
    with sync_playwright() as p:
        ctx = open_context(p, cfg.browser_profile_dir, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.mercadolivre.com.br/ofertas")
        print("Faca login no navegador. Quando /ofertas mostrar produtos, feche a janela.")
        try:
            page.wait_for_event("close", timeout=0)
        finally:
            ctx.close()
    print(f"Sessao salva em {cfg.browser_profile_dir}")


if __name__ == "__main__":
    main()
