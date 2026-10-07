"""Bot de promocoes Mercado Livre -> grupo WhatsApp (via WA-AKG).

  python -m bot.main               # loop infinito a cada INTERVAL_MINUTES
  python -m bot.main --once        # uma rodada
  python -m bot.main --dry-run     # raspa e imprime, nao envia
  python -m bot.main --list-groups # lista grupos da sessao (pegar o JID)
"""
import argparse
import logging
import time

from .config import ROOT, load_config
from .formatter import format_promo
from .scraper import BlockedError, scrape
from .store import Store
from .wa_client import WAClient, WAError

log = logging.getLogger("ml-promo-bot")


def run_once(cfg, wa: WAClient | None, store: Store, dry_run: bool, debug: bool) -> None:
    promos = scrape(
        cfg.ml_urls, cfg.ml_max_pages, cfg.browser_profile_dir, cfg.headless,
        cfg.affiliate_params, debug_dir=ROOT / "debug" if debug else None,
    )
    candidates = sorted(
        (p for p in promos if p.discount >= cfg.min_discount and store.should_send(p.id, p.price)),
        key=lambda p: p.discount,
        reverse=True,
    )[: cfg.max_per_run]
    log.info("%d promocoes raspadas, %d para enviar", len(promos), len(candidates))

    for i, promo in enumerate(candidates):
        text = format_promo(promo)
        if dry_run:
            print(f"\n----- [{promo.id}] img={promo.image}\n{text}")
            continue
        try:
            if promo.image:
                wa.send_image(cfg.wa_group_jid, promo.image, text)
            else:
                wa.send_text(cfg.wa_group_jid, text)
            store.mark_sent(promo.id, promo.price)
            log.info("Enviado %s (%d%% OFF)", promo.id, promo.discount)
        except WAError as e:
            log.error("Falha ao enviar %s: %s", promo.id, e)
        if i < len(candidates) - 1:
            time.sleep(cfg.delay_between_messages)  # evita ban por flood


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-groups", action="store_true")
    ap.add_argument("--debug", action="store_true", help="salva HTML das paginas em debug/")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    wa = None if args.dry_run else WAClient(cfg.wa_base_url, cfg.wa_api_key, cfg.wa_session_id)

    if args.list_groups:
        wa = wa or WAClient(cfg.wa_base_url, cfg.wa_api_key, cfg.wa_session_id)
        for g in wa.list_groups():
            print(f"{g['jid']}\t{g.get('subject')}")
        return

    if not args.dry_run and not cfg.wa_group_jid:
        raise SystemExit("Defina WA_GROUP_JID no .env (use --list-groups)")

    store = Store(cfg.db_path)
    while True:
        try:
            run_once(cfg, wa, store, args.dry_run, args.debug)
        except BlockedError as e:
            log.error(str(e))
            if args.once or args.dry_run:
                raise SystemExit(1)
        except Exception:
            log.exception("Erro na rodada")
        if args.once or args.dry_run:
            break
        log.info("Proxima rodada em %d min", cfg.interval_minutes)
        time.sleep(cfg.interval_minutes * 60)


if __name__ == "__main__":
    main()
