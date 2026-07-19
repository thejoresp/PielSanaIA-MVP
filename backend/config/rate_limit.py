"""Limitador de peticiones por IP.

Vive en su propio módulo para que `main.py` y los controladores puedan compartir la
misma instancia sin importarse entre sí (import circular).

CORS **no** protege estos endpoints: es una restricción del navegador y con `curl` se
saltea. Como la URL del backend viaja pública dentro del bundle del frontend, el rate
limit es la única barrera real contra el abuso de CPU (modelos) y de tokens pagos (IA).

⚠️ Detrás de Nginx, `get_remote_address` ve la IP del proxy y no la del cliente, con lo
   que todos los usuarios comparten el mismo cupo. Correr uvicorn con `--proxy-headers`
   y que Nginx mande `X-Forwarded-For` (ver DESPLIEGUE.md).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Endpoints que ejecutan un modelo local: cuesta CPU, no dinero.
LIMITE_ANALISIS = "20/minute"

# Endpoints que llaman a un proveedor de IA externo: cada request se paga.
LIMITE_IA = "10/minute"
