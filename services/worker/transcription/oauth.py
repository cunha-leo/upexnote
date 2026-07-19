"""
Login social (item 13-C) — OAuth nativo de desktop, SÓ stdlib (sem deps novas):

- Google: Authorization Code + PKCE com redirect de loopback (padrão Google
  para apps instaladas). O client_secret de apps desktop NÃO é confidencial
  (documentado pela Google), mas mesmo assim vive em oauth_config.json, fora
  do binário e do Git.
- GitHub: Device Flow (só client_id, sem secret) — o browser abre em
  github.com/login/device e a pessoa digita o código.

Config: oauth_config.json ao lado do db_config.json (mesma resolução de
caminhos): {"google": {"client_id": "...", "client_secret": "..."},
"github": {"client_id": "..."}}. Sem config → erro claro (o dono regista as
OAuth apps uma única vez, grátis).

Eventos NDJSON no stdout (a app acompanha): progress → done/error.
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

from pathlib import Path

# Resolução própria (não herda a do db_config): o oauth_config.json é
# EMPACOTADO com a app (client IDs de apps desktop não são segredos — a
# segurança é o PKCE), para o instalador funcionar em qualquer máquina
# sem configuração. O AppData fica como override manual, se existir.
if getattr(sys, "frozen", False):
    _appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    _candidates = [
        _appdata / "UpexNote" / "oauth_config.json",
        Path(sys.executable).resolve().parent / "oauth_config.json",
    ]
    OAUTH_CONFIG_PATH = next((p for p in _candidates if p.exists()), _candidates[-1])
else:
    OAUTH_CONFIG_PATH = Path(__file__).resolve().parent / "oauth_config.json"


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _load_oauth_config():
    try:
        return json.loads(OAUTH_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _http_json(url, data=None, headers=None, method=None):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _success_page(ok: bool) -> str:
    """Página de retorno do loopback com a identidade do produto (pedido do
    utilizador, 2026-07-19) — sem recursos externos, funciona offline."""
    title = "Sessão iniciada" if ok else "Pedido inválido"
    body = ("A tua conta foi autenticada com sucesso.<br>"
            "Volta ao <b>UpexNote</b> — esta aba pode ser fechada."
            if ok else
            "Este pedido de autenticação não é válido ou expirou.<br>"
            "Volta ao <b>UpexNote</b> e tenta novamente.")
    icon = "&#10003;" if ok else "&#10007;"
    icon_bg = "#e8b4a0" if ok else "#5c5c6e"
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8">
<title>UpexNote — {title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#16161e; font-family:'Segoe UI Variable Text','Segoe UI',sans-serif; color:#e4e4ef; }}
  .card {{ text-align:center; padding:48px 56px; border:1px solid #2a2a38; border-radius:12px;
           background:#1c1c26; box-shadow:0 8px 40px rgba(0,0,0,.35); max-width:420px; }}
  .badge {{ width:56px; height:56px; border-radius:50%; background:{icon_bg}; color:#16161e;
            font-size:28px; line-height:56px; margin:0 auto 20px; }}
  .brand {{ font-size:22px; font-weight:600; letter-spacing:.2px; margin-bottom:6px; }}
  .brand span {{ color:#e8b4a0; }}
  h1 {{ font-size:17px; font-weight:600; margin:14px 0 8px; }}
  p {{ font-size:14px; color:#a0a0b4; line-height:1.55; margin:0; }}
  .foot {{ margin-top:26px; font-size:12px; color:#5c5c6e; }}
</style></head><body>
<div class="card">
  <div class="badge">{icon}</div>
  <div class="brand">Upex<span>Note</span></div>
  <h1>{title}</h1>
  <p>{body}</p>
  <div class="foot">&copy; UpexFlow &middot; upexflow.com</div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Google — loopback + PKCE
# ---------------------------------------------------------------------------

def _google_flow(cfg):
    client_id = cfg.get("client_id")
    if not client_id:
        return {"ok": False, "error": "oauth_not_configured"}

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)

    result = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ok = q.get("state", [""])[0] == state and "code" in q
            if ok:
                result["code"] = q["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_success_page(ok).encode("utf-8"))
            if ok:
                done.set()

        def log_message(self, *a):  # silêncio
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    redirect = f"http://127.0.0.1:{port}"

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    _emit({"type": "progress", "message": "A abrir o browser para autenticação Google…"})
    webbrowser.open(auth_url)

    if not done.wait(timeout=240):
        server.shutdown()
        return {"ok": False, "error": "timeout"}
    server.shutdown()

    token_req = {
        "client_id": client_id,
        "code": result["code"],
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect,
    }
    if cfg.get("client_secret"):
        token_req["client_secret"] = cfg["client_secret"]
    tok = _http_json("https://oauth2.googleapis.com/token", data=token_req)
    info = _http_json("https://openidconnect.googleapis.com/v1/userinfo",
                      headers={"Authorization": f"Bearer {tok['access_token']}"})
    return {
        "ok": True,
        "auth_provider": "google",
        "provider_id": info.get("sub"),
        "email": info.get("email"),
        "first_name": info.get("given_name"),
        "last_name": info.get("family_name"),
        "provider_scopes": tok.get("scope", "openid email profile"),
    }


# ---------------------------------------------------------------------------
# GitHub — Device Flow (sem secret)
# ---------------------------------------------------------------------------

def _github_flow(cfg):
    client_id = cfg.get("client_id")
    if not client_id:
        return {"ok": False, "error": "oauth_not_configured"}

    scopes = "read:user user:email"
    dev = _http_json("https://github.com/login/device/code",
                     data={"client_id": client_id, "scope": scopes})
    _emit({
        "type": "progress",
        "message": f"Código GitHub: {dev['user_code']} — confirma no browser.",
        "user_code": dev["user_code"],
        "verification_uri": dev["verification_uri"],
    })
    webbrowser.open(dev["verification_uri"])

    deadline = time.time() + int(dev.get("expires_in", 600))
    interval = int(dev.get("interval", 5))
    while time.time() < deadline:
        time.sleep(interval)
        tok = _http_json("https://github.com/login/oauth/access_token", data={
            "client_id": client_id,
            "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        if tok.get("access_token"):
            headers = {"Authorization": f"Bearer {tok['access_token']}",
                       "User-Agent": "UpexNote"}
            user = _http_json("https://api.github.com/user", headers=headers)
            email = user.get("email")
            if not email:
                emails = _http_json("https://api.github.com/user/emails", headers=headers)
                primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
                email = primary.get("email") if primary else None
            name = (user.get("name") or "").split(" ", 1)
            return {
                "ok": True,
                "auth_provider": "github",
                "provider_id": str(user.get("id")),
                "email": email,
                "first_name": name[0] or user.get("login"),
                "last_name": name[1] if len(name) > 1 else None,
                "provider_scopes": tok.get("scope", scopes),
            }
        if tok.get("error") == "slow_down":
            interval += 5
        elif tok.get("error") not in (None, "authorization_pending"):
            return {"ok": False, "error": tok["error"]}
    return {"ok": False, "error": "timeout"}


def run_oauth(provider: str) -> int:
    cfg = (_load_oauth_config() or {}).get(provider)
    if not cfg:
        _emit({"type": "error", "error": "oauth_not_configured",
               "message": "Login social ainda não configurado nesta instalação."})
        return 1
    try:
        res = _google_flow(cfg) if provider == "google" else _github_flow(cfg)
    except Exception as e:  # noqa: BLE001
        _emit({"type": "error", "error": "oauth_failed", "message": str(e)})
        return 1
    if not res.get("ok"):
        _emit({"type": "error", "error": res.get("error", "oauth_failed"),
               "message": "Autenticação não concluída."})
        return 1
    _emit({"type": "oauth", **res})
    return 0
