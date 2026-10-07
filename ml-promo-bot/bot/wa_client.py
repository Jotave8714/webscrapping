"""Cliente minimo da API REST do WA-AKG (../WA-AKG).

Rotas usadas (src/app/api):
  POST /api/messages/{sessionId}/{jid}/send   body: {"message": {...baileys payload}}
  GET  /api/groups/{sessionId}
Autenticacao: header X-API-Key (Dashboard -> Settings -> API Keys).
"""
import logging
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)


class WAError(RuntimeError):
    pass


class WAClient:
    def __init__(self, base_url: str, api_key: str, session_id: str, timeout: int = 60):
        if not api_key or not session_id:
            raise WAError("WA_API_KEY e WA_SESSION_ID sao obrigatorios no .env")
        self.base = f"{base_url}/api"
        self.session_id = session_id
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update({"X-API-Key": api_key, "Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = self.http.request(method, f"{self.base}{path}", timeout=self.timeout, **kwargs)
        try:
            data = resp.json()
        except ValueError:
            raise WAError(f"{method} {path}: HTTP {resp.status_code} resposta nao-JSON")
        if not resp.ok or not data.get("status", False):
            raise WAError(f"{method} {path}: HTTP {resp.status_code} {data.get('message') or data}")
        return data

    def list_groups(self) -> list[dict]:
        return self._request("GET", f"/groups/{quote(self.session_id, safe='')}")["data"]

    def send(self, jid: str, message: dict) -> dict:
        path = f"/messages/{quote(self.session_id, safe='')}/{quote(jid, safe='')}/send"
        return self._request("POST", path, json={"message": message})

    def send_text(self, jid: str, text: str) -> dict:
        return self.send(jid, {"text": text})

    def send_image(self, jid: str, image_url: str, caption: str) -> dict:
        """Envia imagem com legenda; se o WA-AKG falhar ao baixar a imagem, cai para texto."""
        try:
            return self.send(jid, {"image": {"url": image_url}, "caption": caption})
        except WAError as e:
            log.warning("Falha ao enviar imagem (%s), enviando so texto", e)
            return self.send_text(jid, caption)
