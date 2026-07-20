# Análisis del proyecto — PielSana IA

> Documento de contexto generado tras un análisis del código (2026-07-12). Complementa
> `CLAUDE.md` (raíz) y `.claude/agents/pielsana.md`; no los repite, los amplía con hallazgos
> del código real. Actualizar cuando la arquitectura cambie.
>
> **Para la deuda técnica pendiente ver [`AUDITORIA.md`](../AUDITORIA.md)** (auditoría completa
> del 2026-07-19, con hallazgos numerados y checkboxes). La tabla de la §5 de acá quedó
> subsumida por ese documento.

## 1. Qué es

MVP de análisis de piel por IA. El usuario sube una foto, elige un tipo de análisis y recibe una
clasificación de condiciones cutáneas más descripción y recomendaciones. **Herramienta educativa /
de autocuidado, no diagnóstico médico.**

Dos servicios independientes en un monorepo, que se comunican solo por HTTP:

```
Frontend (React SPA, GitHub Pages, HTTPS)
        │  fetch  ${VITE_API_URL}/skin/...
        ▼
Backend (FastAPI, EC2, HTTP :8080)
        ├── modelos locales Keras/TensorFlow (CPU)  → clasificación
        ├── DeepSeek deepseek-v4-flash (texto)      → descripción + recomendaciones
        └── OpenAI gpt-4o (visión, OPCIONAL)        → detección desde la imagen
```

## 2. Backend (`backend/`, FastAPI + Python 3.10)

| Archivo | Rol |
|---|---|
| `main.py` | Instancia FastAPI, `logging`, CORS por `FRONTEND_ORIGINS`, registro del rate limiter, warmup de modelos en el `startup`. `GET /` describe la API y `GET /health` reporta el estado de cada modelo. |
| `controllers/skin.py` | Solo endpoints y validación de entrada. |
| `services/skin_analysis_service.py` | `_ModeloKeras` (carga perezosa cacheada, con `threading.Lock`) + `_clasificar_multiclase` / `_clasificar_binario`. Expone `predict_*_class` y `precargar_modelos()`. |
| `config/model_config.py` | Rutas de modelos (override por env), fuerza CPU, limita threads, crea dirs. |
| `config/rate_limit.py` | Instancia compartida de `slowapi` + los dos límites. |

### Flujo de predicción (contrato a respetar)
1. `predict_*_class(image_bytes)` delega en un `_ModeloKeras`, que carga el `.keras` la primera vez
   (protegido por lock) o lo toma del cache. El `startup` ya los precarga.
2. Preprocesado **uniforme**: `RGB → resize 224x224 → /255.0 → reshape (1,224,224,3)`.
3. Si el modelo no carga o falla → devuelve `(None, None)` → el endpoint responde **500**. No romper esto.
4. La inferencia se invoca siempre con `await run_in_threadpool(...)`: es CPU-bound y bloquearía
   el event loop.

### Modelos y salidas
- **Lunares** (`ham10000/lunares.keras`): multiclase, 7 clases HAM10000 (`argmax`).
  Clases → etiquetas ES: `akiec`=Queratosis Actínica, `bcc`=Carcinoma Basocelular, `bkl`=Queratosis
  Benigna, `df`=Dermatofibroma, `mel`=Melanoma, `nv`=Lunar Común (Nevus), `vasc`=Lesión Vascular.
- **Acné** (`acne/acne.keras`): binario sigmoide, `> 0.5` → "Con acné" / "Sin acné".
- **Rosácea** (`rosacea/rosacea.keras`): binario sigmoide, `> 0.5` → "Con rosácea" / "Sin rosácea".
- Los `.keras` **no están versionados** (gitignored, solo `.gitkeep`). Sin ellos → 500.

### Endpoints (prefijo `/skin`)
- `POST /api/analyze` y `POST /api/analyze-lunares` — lunares, resultado completo directo
  (sin dict en memoria; el front lo pasa por `navigate(state)`).
- `POST /api/analyze-acne`, `POST /api/analyze-rosacea` — binarios.
- `POST /openai-analizar` — imagen → **OpenAI gpt-4o** (visión) → JSON `{afeccion, descripcion, recomendaciones}`. Opcional: sin `OPENAI_API_KEY` → 503.
- `POST /openai-recomendaciones` — `{prediccion}` → **DeepSeek** → `{descripcion, recomendaciones}`.
  El body solo acepta una de las **11 etiquetas** de los modelos; otro texto → 422 (anti prompt injection).
  (La ruta mantiene el nombre `openai-*` por compatibilidad con el frontend.)
- Fuera de `/skin`: `GET /health` y `GET /`.
- **Rate limiting por IP** (`slowapi`): 20/min en los endpoints de modelo, 10/min en los de IA.
  Detrás de Nginx hace falta `uvicorn --proxy-headers`.
- Las vistas HTML (`/skin/`, `/skin/results`) y `POST /skin/upload` **se eliminaron**: el backend
  solo devuelve JSON.

## 3. Frontend (`frontend/`, React 18 + TS + Vite + Tailwind)

- Ruteo con `react-router-dom` (`App.tsx`): `Home`, `results` (Lunares), `results-acne`,
  `results-rosacea`, `results-openai`, `conditions/:condition`, `about`. Todas salvo `Home` van
  con `React.lazy`. `BrowserRouter` usa `basename={import.meta.env.BASE_URL}`.
- **Organizado por capas** (ver la tabla en `CLAUDE.md`): `api/` · `types/` · `constants/` ·
  `hooks/` · `data/` · `components/{ui,upload,results}/` · `pages/`.
- **Assets desde JSX con `import.meta.env.BASE_URL`**, nunca ruta absoluta: Vite reescribe el
  `index.html` con la `base` pero no las cadenas del JSX (daba 404 en subruta).
- **Ningún componente hace `fetch`**: todo pasa por `api/skin.ts`, y `api/client.ts` traduce los
  errores a un `ApiError` con mensaje listo para mostrar (incluye 429 del rate limiting).
  Se renderiza con `<BannerError />`; ya no hay `alert()`.
- **Flujo de subida** (`components/upload/`): `SelectorTipoAnalisis` (lee el catálogo de
  `constants/analisis.ts`) → `ConsentModal` (Ley 25.326, obligatorio) → `ZonaDeSubida` →
  `VistaPreviaImagen`. El estado vive en `hooks/useAnalisisImagen.ts`; `ImageUploader` solo compone.
  Agregar un tipo de análisis = una entrada en el catálogo + su ruta en `App.tsx`.
- **Páginas de resultados**: las 4 comparten `components/results/ResultadoLayout.tsx`, donde vive
  el disclaimer médico una sola vez. Los cuatro flujos pasan el resultado por `navigate(state)`,
  que no sobrevive a un refresh → de ahí `SinResultado`.
- `main.tsx` monta un `ErrorBoundary`; sin él una excepción en render dejaba pantalla en blanco.
- Todas las llamadas usan `import.meta.env.VITE_API_URL` como base. Si falta, `api/client.ts`
  loguea un error explícito en consola. Debe definirse **antes** de `npm run build`.
  Plantilla en `frontend/.env.example`.
- `package.json` ya se llama `pielsana-ia` (antes `dermascan-skin-analysis`).
- El modal de consentimiento apunta a `contacto@pielsanaia.click`, correo del dominio **vencido**;
  está aislado en la constante `CONTACTO_DATOS` de `components/upload/ConsentModal.tsx`.

## 4. Despliegue

- **Backend:** EC2 Ubuntu 22.04 `t2.micro`, IP `54.82.199.243`. Scripts: `infra.sh` (VPC/SG/EC2/IP
  elástica), `dockerUbuntu.txt` (user-data instala Docker), `reboot_backend.sh` (rebuild+run en :8080),
  `nginx_manager.sh` (reverse proxy), `connect_aws.sh` (SSH con `vockey.pem`).
- **Frontend:** `npm run deploy` (gh-pages → GitHub Pages, HTTPS).
- **Dominio propio `pielsanaia.click` vencido** (no se renueva). Plan gratis: frontend en
  `https://USUARIO.github.io/PielSanaIA-MVP`, backend en VPS fijo detrás de HTTPS con DuckDNS + Let's Encrypt.
- Plantillas de env versionadas: `.env.example` (raíz, backend) y `frontend/.env.example`.

## 5. Deuda técnica / puntos críticos (verificados en el código)

| # | Problema | Dónde | Impacto |
|---|---|---|---|
| 1 | **Mixed content**: front HTTPS → back HTTP bloqueado por el navegador; **dominio `pielsanaia.click` vencido** (plan gratis: GitHub Pages + VPS con DuckDNS/Let's Encrypt) | despliegue | Producción rota sin TLS en el backend |
| 2 | ✅ **RESUELTO** — `print` de `OPENAI_API_KEY` eliminado | `skin.py` | Ya no se loguea el secreto |
| 3 | ✅ **RESUELTO** — estado en memoria (`lunares_results`) eliminado; backend sin estado | `skin.py` | Ya no hay leak ni pérdida al reiniciar |
| 4 | ✅ **RESUELTO** — CORS configurable por `FRONTEND_ORIGINS` (ya no `["*"]`) | `main.py` | Definir origen real en prod |
| 3b | ✅ **AÑADIDO** — validación de subida (tipo/tamaño 8 MB/decodificable) vía `leer_imagen_validada()` | `skin.py` | Protege CPU y costo OpenAI |
| 5 | **TensorFlow 2.19.0** sin wheels para Python ≥3.13 | `requirements.txt` | Dev local con Python 3.10–3.12 o Docker |
| 6 | ✅ **RESUELTO** — `requirements.txt` con versiones fijas y `transformers` (sin uso) eliminado; deps de test en `requirements-dev.txt` | `backend/` | Builds reproducibles (validar pines con un `docker build`) |
| 7 | ✅ **RESUELTO** — `vite.config.ts` con `base` configurable (`VITE_BASE`, default `/`) | frontend | Assets correctos en subruta o dominio propio |
| 8 | ✅ **RESUELTO** — endpoints de clasificación deduplicados con `analizar_con_modelo()`; preprocesado unificado en `_preprocesar_imagen()`; llamadas a IA centralizadas en `_completar_chat()` (`llamar_deepseek` / `llamar_openai_vision`) con manejo de errores (502/503) | `skin.py`, `skin_analysis_service.py` | Menos superficie de bugs |
| 9 | ✅ **RESUELTO** — suite `pytest` en `backend/tests/` (modelos mockeados) | `backend/tests/` | Red de seguridad básica |
| 10 | ✅ **RESUELTO** — `setup-lightshot.exe` (2.7 MB) y `.gitignore.bak` eliminados con `git rm`; `.gitignore` ahora ignora `*.exe`/`*.bak` | repo | Repo limpio |
| 11 | ✅ **RESUELTO** — `leer_imagen_validada` lee por fragmentos (64 KB) y corta apenas supera 8 MB; ya no carga la subida entera antes de rechazarla | `skin.py` | Mitigación DoS efectiva |
| 12 | ✅ **RESUELTO** — drag & drop funciona; hoy vive en `ZonaDeSubida.tsx`, que comparte el mismo callback entre el drop y el input | `components/upload/` | Arrastrar imagen carga la vista previa |
| 13 | ✅ **RESUELTO** — `package.json` renombrado a `pielsana-ia`; imports muertos eliminados; `/upload`, `/skin/` y `/skin/results` borrados; `print()` migrado a `logging` (cero `print` en `backend/`) | repo | Limpieza saldada |
| 14 | ✅ **AÑADIDO** — plantillas `.env.example` (raíz/backend) y `frontend/.env.example` | repo | Onboarding/despliegue con las env vars documentadas |
| 15 | Pendiente: **email de contacto** `contacto@pielsanaia.click` quedó en el dominio vencido | `upload/ConsentModal.tsx` (`CONTACTO_DATOS`) | Actualizar a un correo válido; también difiere del del README |
| 16 | Pendiente: **sin CI** (no hay `.github/workflows/`); la suite pytest existe pero nada la corre automáticamente | repo | Sin red de seguridad automática |
| 17 | ✅ **RESUELTO** — endurecimiento de seguridad: límite de resolución (40 MP, corta bombas de descompresión), allowlist de `content_type`, rate limiting por IP con `slowapi`, allowlist de etiquetas contra prompt injection, errores sin detalles internos, `timeout` en el cliente de IA | `skin.py`, `config/rate_limit.py` | Ver AUDITORIA.md A13/A14/A2/A3/A4/A15 |
| 18 | ✅ **RESUELTO** — el event loop ya no se bloquea: `run_in_threadpool` en la inferencia **y** en las llamadas a los proveedores (el cliente OpenAI es síncrono) | `skin.py` | Concurrencia real |
| 19 | ✅ **RESUELTO** — deduplicación: `_ModeloKeras` + `_clasificar_*` en el servicio; `data/conditions.py` fuera del controlador | backend | Menos superficie de bugs |
| 20 | ✅ **AÑADIDO** — `GET /health` con estado por modelo + warmup de modelos en el `startup` (con `threading.Lock`) | `main.py`, servicio | Destraba HEALTHCHECK y monitoreo |
| 21 | ✅ **RESUELTO** — frontend reestructurado por capas (`api/`, `types/`, `constants/`, `hooks/`, `data/`, `components/{ui,upload,results}/`); `ImageUploader` 343→76 líneas; las 4 páginas de resultados comparten `ResultadoLayout`; `ErrorBoundary`, `basename` y code splitting. Bundle inicial 218→186 KB | `frontend/src/` | Ver AUDITORIA.md C2/C3/C4/C5/C9/S12 |
| 22 | ✅ **RESUELTO** — auditoría posterior al refactor: logo con ruta absoluta (404 en subruta, dejaba [C3] a medias), CSS muerto, `color-scheme` fijo en light, `URL_TURNOS` duplicada, `DarkModeToggle` fuera de su capa, dependencia sin usar | `frontend/src/` | Ver AUDITORIA.md C14-C18 |
| 23 | Pendiente: **dos caminos de deploy** — `package.json` mantiene `gh-pages` mientras `DESPLIEGUE.md` define Vercel | `package.json` | Ver AUDITORIA.md C19 |
| 24 | Pendiente: el toggle de tema **congela `prefers-color-scheme`** al persistir en el montaje inicial | `ui/DarkModeToggle.tsx` | Ver AUDITORIA.md C20 |

## 6. Convenciones (no romper)

- **Idioma español** en código, comentarios, labels y mensajes de API.
- **Pydantic v1** (1.10.15) — sintaxis v1.
- Preprocesado de imágenes uniforme (ver §2).
- Contrato `(None, None)` → 500 en modelos que no cargan.
- Tono clínico: educativo/autocuidado, no diagnóstico; mensaje de privacidad (imágenes temporales,
  no se almacenan) intacto.
- Git: **sin** trailer `Co-Authored-By: Claude`.

## 7. Verificación rápida

- Backend: `uvicorn backend.main:app --reload` (desde la raíz) y probar el endpoint afectado.
- Frontend: `npm run dev`, comprobar flujo en el navegador, `npm run lint` y `npm run build`.
