# Arquitectura, comandos y configuración

> Referencia de consulta. Las reglas que hay que respetar siempre viven en el
> [`CLAUDE.md`](../CLAUDE.md) de la raíz; las convenciones de cada servicio, en
> `backend/CLAUDE.md` y `frontend/CLAUDE.md`.

## Estructura

Monorepo con dos servicios independientes que se comunican por HTTP. El backend
**solo devuelve JSON** (no sirve HTML).

- **`backend/`** — API REST con **FastAPI** (Python 3.10).
  - `controllers/skin.py` — solo endpoints y validación de entrada; sin datos ni lógica de modelos.
  - `services/skin_analysis_service.py` — clase `_ModeloKeras` (carga perezosa cacheada y **con
    `threading.Lock`**) + los ayudantes `_clasificar_multiclase` / `_clasificar_binario`. Expone
    `predict_*_class` y `precargar_modelos()`.
  - Los `.keras` **no están versionados en git**; van en `backend/modelos/{ham10000,acne,rosacea}/`.
- **`frontend/`** — SPA con **React 18 + TypeScript + Vite + Tailwind**, ruteo con
  `react-router-dom`. Organizado por capas, con tres carpetas que tienen reglas propias:

  | Carpeta | Regla |
  |---|---|
  | `src/api/` | `client.ts` (URL base, `ApiError`, mensajes por código HTTP) y `skin.ts` (una función por endpoint). **Ningún componente hace `fetch` directo.** |
  | `src/data/` | **Contenido estático** que no depende del backend: `condiciones.ts` (las 4 fichas de condiciones). |
  | `src/constants/` | `analisis.ts` (catálogo de tipos de análisis: clave, etiqueta, endpoint, ruta) y `enlaces.ts` (URLs externas compartidas). |

  - **Agregar un tipo de análisis** = una entrada en `constants/analisis.ts` + su ruta en `App.tsx`.
    No hay `if/else` por tipo en ningún componente.
  - El **disclaimer médico** vive una sola vez, en `results/ResultadoLayout.tsx`.
  - Las rutas distintas del home se cargan con `React.lazy` (`App.tsx`).

## Comandos

Los scripts de npm y los `requirements.txt` están en sus manifiestos. Lo que **no** es obvio:

```bash
# Backend en desarrollo: desde la raíz del repo — el paquete es backend.main
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

# Tests: desde la raíz; los modelos se mockean, no requieren los .keras
python -m pytest backend/tests

# Docker: el contexto de build es la raíz, no backend/
sudo docker build -t pielsana-backend -f backend/Dockerfile .
sudo docker run -d --rm --name pielsana-backend -p 8080:8080 pielsana-backend
# ./reboot_backend.sh reconstruye y relanza el contenedor
```

`backend/requirements-dev.txt` es solo para los tests (pytest, httpx).

## Variables de entorno

> Plantillas versionadas: **`.env.example`** (raíz, backend) y **`frontend/.env.example`**.
> Copiarlas a `.env` / `frontend/.env` y completar; los `.env` reales no se commitean.

**Backend** (`.env` en la raíz):

- `DEEPSEEK_API_KEY` — **requerida** para `/skin/openai-recomendaciones` (texto). API compatible con
  OpenAI (`base_url https://api.deepseek.com`).
- `DEEPSEEK_MODEL` — opcional, default `deepseek-v4-flash` (`deepseek-chat`/`deepseek-reasoner` se
  deprecan el 2026/07/24).
- `OPENAI_API_KEY` — **opcional**, solo para `/skin/openai-analizar` (visión gpt-4o). Sin ella ese
  endpoint responde 503; el resto funciona con DeepSeek.
- `OPENAI_VISION_MODEL` — opcional, default `gpt-4o`.
- `FRONTEND_ORIGINS` — orígenes permitidos por CORS, lista separada por comas. Default: dev local
  (`http://localhost:5173,http://127.0.0.1:5173`). **En producción definirla** con la URL del frontend.
- `LUNARES_MODEL_PATH`, `ACNE_MODEL_PATH`, `ROSACEA_MODEL_PATH` — rutas de los `.keras` (tienen default).
- `LOG_LEVEL` — opcional, default `INFO`. Nivel del `logging` configurado en `main.py`.

**Frontend** (`frontend/.env`, en build time — Vite):

- `VITE_API_URL` — URL base del backend. TODO el frontend llama a `${VITE_API_URL}/skin/...`.
  Si falta, las peticiones apuntan a `undefined/skin/...` y fallan. Debe definirse **antes** de
  `npm run build`.
- `VITE_BASE` — ruta base del build (`vite.config.ts`). Default `/` (dominio propio / raíz). Para
  GitHub Pages en subruta (`usuario.github.io/REPO`) definir `VITE_BASE="/REPO/"` antes de
  `npm run build`.
