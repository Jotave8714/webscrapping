from .scraper import Promo


def brl(value: float) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_promo(p: Promo) -> str:
    lines = [f"🔥 *{p.title}*", ""]
    if p.old_price:
        lines.append(f"~De {brl(p.old_price)}~")
    lines.append(f"💰 *Por {brl(p.price)}*" + (f"  ({p.discount}% OFF)" if p.discount else ""))
    if p.installments:
        lines.append(f"💳 {p.installments}")
    if p.free_shipping:
        lines.append("🚚 Frete grátis")
    lines += ["", f"🛒 {p.url}"]
    return "\n".join(lines)
