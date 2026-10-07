# ml-promo-bot

Bot que raspa promoções do Mercado Livre e posta num grupo do WhatsApp usando o
gateway [WA-AKG](../WA-AKG) (API REST).

```
Mercado Livre /ofertas ──Playwright──▶ filtro (desconto, dedupe SQLite) ──▶ WA-AKG REST ──▶ grupo WhatsApp
```

## Setup

### 1. WA-AKG
1. Suba o WA-AKG (`cd ../WA-AKG && npm install && npm run db:push && npm run dev`).
2. No dashboard: crie uma sessão e escaneie o QR code com o número do bot.
3. Adicione esse número ao grupo de promoções.
4. Dashboard → Settings → API Keys → gere uma chave (`wag_...`).

### 2. Bot
```bash
cd ml-promo-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # preencha WA_API_KEY, WA_SESSION_ID
python -m bot.main --list-groups   # copie o JID do grupo (…@g.us) para WA_GROUP_JID
```

### 3. Login no Mercado Livre (uma vez)
O ML redireciona tráfego automatizado para `/gz/account-verification` ("acesse sua conta").
O bot usa um perfil de navegador persistente, então basta logar uma vez:
```bash
python -m bot.login
```
Faça login na janela, confirme que `/ofertas` mostra produtos e feche. Repita se o bot logar
`Mercado Livre pediu login/verificacao`.

## Uso
```bash
python -m bot.main --dry-run          # raspa e imprime as mensagens, sem enviar
python -m bot.main --dry-run --debug  # salva HTML das páginas em debug/ (ajustar seletores)
python -m bot.main --once             # uma rodada com envio
python -m bot.main                    # loop a cada INTERVAL_MINUTES
```

## Configuração (`.env`)
| Var | Função |
|---|---|
| `ML_URLS` | páginas de oferta, separadas por vírgula (ex.: `/ofertas`, `/ofertas?category=MLB1051`) |
| `MIN_DISCOUNT` | desconto mínimo (%) para postar |
| `MAX_PER_RUN` | máx. de mensagens por rodada |
| `DELAY_BETWEEN_MESSAGES` | segundos entre mensagens (anti-ban) |
| `ML_AFFILIATE_PARAMS` | query de afiliado anexada aos links |
| `HEADLESS` | `false` para ver o navegador |

Repostagem: um item só é reenviado se o preço cair ou após 3 dias (`bot/store.py`).

## Estrutura
- `bot/scraper.py` — Playwright + extração dos cards (`poly-card`)
- `bot/wa_client.py` — cliente WA-AKG (`POST /api/messages/{session}/{jid}/send`, `GET /api/groups/{session}`)
- `bot/formatter.py` — texto da mensagem (markdown do WhatsApp)
- `bot/store.py` — dedupe SQLite
- `bot/main.py` — CLI / loop
