import hashlib
import hmac
import time
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from backend.core.config import settings

router = APIRouter()

_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MedSim — Acceso</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0f1117;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .card {
      background: #1a1d2e;
      border: 1px solid #2a2d3e;
      border-radius: 12px;
      padding: 2.5rem 2rem;
      width: 100%;
      max-width: 360px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    h1 { color: #e2e8f0; font-size: 1.5rem; margin-bottom: 0.25rem; }
    p  { color: #64748b; font-size: 0.875rem; margin-bottom: 2rem; }
    label { display: block; color: #94a3b8; font-size: 0.8rem;
            font-weight: 500; margin-bottom: 0.4rem; letter-spacing: 0.05em; }
    input[type=password] {
      width: 100%; padding: 0.65rem 0.9rem;
      background: #0f1117; border: 1px solid #2a2d3e; border-radius: 8px;
      color: #e2e8f0; font-size: 0.95rem; outline: none;
      transition: border-color .2s;
    }
    input[type=password]:focus { border-color: #6366f1; }
    button {
      margin-top: 1.25rem; width: 100%;
      padding: 0.7rem; background: #6366f1; border: none; border-radius: 8px;
      color: #fff; font-size: 0.95rem; font-weight: 600; cursor: pointer;
      transition: background .2s;
    }
    button:hover { background: #4f46e5; }
    .error {
      margin-top: 1rem; padding: 0.6rem 0.9rem;
      background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3);
      border-radius: 8px; color: #f87171; font-size: 0.85rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>MedSim</h1>
    <p>Simulador de entrevista médico-paciente</p>
    <form method="post" action="/auth/login">
      <input type="hidden" name="next" value="{next}">
      <label for="password">CONTRASEÑA</label>
      <input id="password" name="password" type="password"
             placeholder="Ingresá la contraseña" autofocus required>
      {error}
      <button type="submit">Ingresar</button>
    </form>
  </div>
</body>
</html>"""


def _make_token(password: str) -> str:
    """Genera un token HMAC firmado con timestamp para la cookie de sesión."""
    ts = str(int(time.time()))
    h = hmac.new(settings.SECRET_KEY.encode(), f"{password}:{ts}".encode(), hashlib.sha256).hexdigest()
    return f"{ts}:{h}"


def _verify_token(token: str, max_age_seconds: int = 86400 * 30) -> bool:
    """Valida el token de sesión. Caduca a los 30 días por defecto."""
    if not settings.SITE_PASSWORD:
        return True
    try:
        ts_str, h = token.split(":", 1)
        ts = int(ts_str)
    except (ValueError, AttributeError):
        return False
    if time.time() - ts > max_age_seconds:
        return False
    expected = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{settings.SITE_PASSWORD}:{ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(h, expected)


def is_authenticated(request: Request) -> bool:
    """Comprueba si la request tiene sesión válida."""
    if not settings.SITE_PASSWORD:
        return True
    token = request.cookies.get("medsim_session")
    return bool(token and _verify_token(token))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/frontend/index", error: str = ""):
    err_html = f'<div class="error">Contraseña incorrecta.</div>' if error else ""
    return HTMLResponse(_LOGIN_PAGE.format(next=next, error=err_html))


@router.post("/login")
async def login_submit(
    response: Response,
    password: str = Form(...),
    next: str = Form(default="/frontend/index"),
):
    if settings.SITE_PASSWORD and password != settings.SITE_PASSWORD:
        return RedirectResponse(url=f"/auth/login?next={next}&error=1", status_code=303)

    token = _make_token(password if settings.SITE_PASSWORD else "open")
    redirect = RedirectResponse(url=next, status_code=303)
    redirect.set_cookie(
        key="medsim_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,   # cambiar a True cuando se use HTTPS
        max_age=86400 * 30,
    )
    return redirect


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("medsim_session")
    return response
