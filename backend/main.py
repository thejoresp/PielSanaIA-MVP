from fastapi import FastAPI
import uvicorn
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from backend.controllers import skin

# Cargar variables de entorno del archivo .env
# Es bueno hacerlo lo antes posible
load_dotenv()

# Opcional: Verificar si el token se cargó (para depuración)
# print(f"HF_TOKEN desde el entorno: {os.getenv('HF_TOKEN')}")

# Crear la instancia de la aplicación FastAPI
app = FastAPI(
    title="PielSana IA",
    description="Sistema de análisis facial para clasificar condiciones cutáneas.",
    version="0.1.0"
)

# Habilitar CORS para el frontend en desarrollo y producción.
# Los orígenes permitidos se configuran con la variable de entorno FRONTEND_ORIGINS
# (lista separada por comas). En producción DEBE definirse con la URL del frontend
# (p. ej. la de GitHub Pages / dominio propio). Por defecto solo se permite el dev local.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoint de prueba
@app.get("/")
async def read_root():
    # Redirigir a la página de carga de la aplicación de piel
    return RedirectResponse(url="/skin/")

# Registrar routers de los controladores
app.include_router(skin.router, prefix="/skin", tags=["Skin Analysis Frontend"])

if __name__ == "__main__":
    # Esta sección es útil para desarrollo, pero para producción usarás 'run.py'
    uvicorn.run(app, host="0.0.0.0", port=8080) 