"""Punto de entrada de la API de PielSana IA.

Levantar desde la raíz del repo:
    uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

Detrás de un reverse proxy agregar `--proxy-headers`, si no el rate limiting por IP
ve siempre la dirección del proxy (ver `backend/config/rate_limit.py`).
"""
import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config.rate_limit import limiter
from backend.controllers import skin
from backend.services.skin_analysis_service import precargar_modelos

# Cargar variables de entorno del archivo .env lo antes posible.
load_dotenv()

# Logging con timestamps y niveles, en vez de `print`: en producción se puede filtrar
# y silenciar. `LOG_LEVEL` permite subir a DEBUG sin tocar el código.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

VERSION = "0.1.0"

app = FastAPI(
    title="PielSana IA",
    description="Sistema de análisis facial para clasificar condiciones cutáneas.",
    version=VERSION,
)

# Habilitar CORS para el frontend en desarrollo y producción.
# Los orígenes permitidos se configuran con la variable de entorno FRONTEND_ORIGINS
# (lista separada por comas). En producción DEBE definirse con la URL del frontend.
# Por defecto solo se permite el dev local.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

# Rate limiting por IP (ver backend/config/rate_limit.py). Los decoradores
# @limiter.limit(...) de los endpoints necesitan que el limiter esté en app.state.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def cargar_modelos_al_arrancar():
    """Carga los modelos antes de atender tráfico.

    Sin esto la carga cae dentro del primer request (varios segundos) y dos peticiones
    simultáneas en frío podían duplicar el pico de RAM.
    """
    logger.info("Orígenes CORS permitidos: %s", allowed_origins)
    app.state.modelos = precargar_modelos()
    faltantes = [nombre for nombre, ok in app.state.modelos.items() if not ok]
    if faltantes:
        logger.warning(
            "Modelos no disponibles: %s. Los endpoints de predicción responderán 500. "
            "Copiar los .keras a backend/modelos/.",
            ", ".join(faltantes),
        )


@app.get("/health", tags=["Infra"])
async def health():
    """Estado del servicio, para Nginx, el HEALTHCHECK de Docker y monitores de uptime."""
    return {
        "status": "ok",
        "version": VERSION,
        "modelos": getattr(app.state, "modelos", {}),
    }


@app.get("/", tags=["Infra"])
async def read_root():
    """La raíz describe la API; el HTML lo sirve el frontend, no este servicio."""
    return {"servicio": "PielSana IA", "version": VERSION, "docs": "/docs", "health": "/health"}


# Registrar routers de los controladores
app.include_router(skin.router, prefix="/skin", tags=["Skin Analysis API"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
