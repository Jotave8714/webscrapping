import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Carrega .env simples (KEY=VALUE) sem sobrescrever variaveis ja definidas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    wa_base_url: str
    wa_api_key: str
    wa_session_id: str
    wa_group_jid: str
    ml_urls: list[str]
    ml_max_pages: int
    min_discount: int
    max_per_run: int
    headless: bool
    browser_profile_dir: Path
    affiliate_params: str
    interval_minutes: int
    delay_between_messages: int
    db_path: Path


def load_config() -> Config:
    _load_dotenv(ROOT / ".env")
    env = os.environ.get

    def path(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    return Config(
        wa_base_url=env("WA_BASE_URL", "http://localhost:3000").rstrip("/"),
        wa_api_key=env("WA_API_KEY", ""),
        wa_session_id=env("WA_SESSION_ID", ""),
        wa_group_jid=env("WA_GROUP_JID", ""),
        ml_urls=[u.strip() for u in env("ML_URLS", "https://www.mercadolivre.com.br/ofertas").split(",") if u.strip()],
        ml_max_pages=int(env("ML_MAX_PAGES", "2")),
        min_discount=int(env("MIN_DISCOUNT", "20")),
        max_per_run=int(env("MAX_PER_RUN", "10")),
        headless=env("HEADLESS", "true").lower() == "true",
        browser_profile_dir=path(env("BROWSER_PROFILE_DIR", "./.browser-profile")),
        affiliate_params=env("ML_AFFILIATE_PARAMS", "").lstrip("?&"),
        interval_minutes=int(env("INTERVAL_MINUTES", "30")),
        delay_between_messages=int(env("DELAY_BETWEEN_MESSAGES", "15")),
        db_path=path(env("DB_PATH", "./promos.db")),
    )
