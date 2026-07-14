# Análisis del proyecto — PielSana IA

> Documento de contexto generado tras un análisis del código (2026-07-12). Complementa
> `CLAUDE.md` (raíz) y `.claude/agents/pielsana.md`; no los repite, los amplía con hallazgos
> del código real. Actualizar cuando la arquitectura cambie.

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
| `main.py` | Instancia FastAPI, CORS configurable por `FRONTEND_ORIGINS` (ya no `["*"]`), monta `skin.router` bajo `/skin`. `GET /` redirige a `/skin/`. |
| `controllers/skin.py` | Todos los endpoints + `conditions_data` embebido + router OpenAI. |
| `services/skin_analysis_service.py` | Carga perezosa de los 3 `.keras` (cacheados en globales) y predicción. |
| `config/model_config.py` | Rutas de modelos (override por env), fuerza CPU, limita threads, crea dirs. |
| `models/condition.py` | Pydantic v1 `ConditionInfo`. |

### Flujo de predicción (contrato a respetar)
1. `predict_*_class(image_bytes)` llama a `load_*_model()` (perezoso, cachea en global).
2. Preprocesado **uniforme**: `RGB → resize 224x224 → /255.0 → reshape (1,224,224,3)`.
3. Si el modelo no carga o falla → devuelve `(None, None)` → el endpoint responde **500**. No romper esto.

### Modelos y salidas
- **Lunares** (`ham10000/lunares.keras`): multiclase, 7 clases HAM10000 (`argmax`).
  Clases → etiquetas ES: `akiec`=Queratosis Actínica, `bcc`=Carcinoma Basocelular, `bkl`=Queratosis
  Benigna, `df`=Dermatofibroma, `mel`=Melanoma, `nv`=Lúnar Común (Nevus), `vasc`=Lesión Vascular.
- **Acné** (`acne/acne.keras`): binario sigmoide, `> 0.5` → "Con acné" / "Sin acné".
- **Rosácea** (`rosacea/rosacea.keras`): binario sigmoide, `> 0.5` → "Con rosácea" / "Sin rosácea".
- Los `.keras` **no están versionados** (gitignored, solo `.gitkeep`). Sin ellos → 500.

### Endpoints (prefijo `/skin`)
- `POST /api/analyze` y `POST /upload` — lunares, devuelven predicción directa (casi duplicados).
- `POST /api/analyze-lunares` — lunares, devuelve el resultado completo directo (ya sin dict en memoria
  ni `GET /api/analyze-lunares/{id}`; el front lo pasa por `navigate(state)`).
- `POST /api/analyze-acne`, `POST /api/analyze-rosacea` — binarios.
- `GET /api/condition/{nombre}` — info estática (`rosacea`, `acne`, `manchas`, `lunares`).
- `POST /openai-analizar` — imagen → **OpenAI gpt-4o** (visión) → JSON `{afeccion, descripcion, recomendaciones}`. Opcional: sin `OPENAI_API_KEY` → 503.
- `POST /openai-recomendaciones` — `{prediccion}` → **DeepSeek** → `{descripcion, recomendaciones}`. (La ruta mantiene el nombre `openai-*` por compatibilidad con el frontend, aunque el proveedor sea DeepSeek.)
- Las vistas HTML (`GET /skin/`, `/skin/results`) devuelven **404 a propósito** (las sirve el frontend).

## 3. Frontend (`frontend/`, React 18 + TS + Vite + Tailwind)

- Ruteo con `react-router-dom` (`App.tsx`): `Home`, `results` / `results/:id` (Lunares),
  `results-acne`, `results-rosacea`, `results-openai`, `conditions/:condition`, `about`.
- **Una página de resultados por modelo.** Los cuatro flujos pasan el resultado por `navigate(state)`
  (lunares se unificó con acné/rosácea/openai; ya no usa `id` ni backend con estado).
- `components/ImageUploader.tsx` es el corazón del flujo: 4 tarjetas de análisis
  (`acne`, `rosacea`, `moles`, `openai`) → modal de **consentimiento** (Ley 25.326) obligatorio →
  selección de imagen → `handleAnalyze()` enruta al endpoint según `analysisType`.
- Todas las llamadas usan `import.meta.env.VITE_API_URL` como base → `${VITE_API_URL}/skin/...`.
  Si falta, apunta a `undefined/skin/...` y falla. Debe definirse **antes** de `npm run build`.
  Plantilla en `frontend/.env.example`.
- `package.json` ya se llama `pielsana-ia` (antes `dermascan-skin-analysis`).
- El modal de consentimiento apunta a `contacto@pielsanaia.click`, correo del dominio **vencido**;
  actualizar cuando haya uno nuevo.

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
| 12 | ✅ **RESUELTO** — drag & drop funciona: `handleDrop` procesa el archivo soltado vía `processFile()` compartido con el input | `ImageUploader.tsx` | Arrastrar imagen ahora carga la vista previa |
| 13 | ✅ **RESUELTO parcialmente** — `package.json` renombrado a `pielsana-ia`; imports muertos (`Path`, `asyncio`, `RedirectResponse`) eliminados de `skin.py`. **Pendiente:** `/upload` legacy aún duplica `/api/analyze`; `print()` usado como logging (migrar a `logging`) | repo | Limpieza menor |
| 14 | ✅ **AÑADIDO** — plantillas `.env.example` (raíz/backend) y `frontend/.env.example` | repo | Onboarding/despliegue con las env vars documentadas |
| 15 | Pendiente: **email de contacto** `contacto@pielsanaia.click` (modal de consentimiento) quedó en el dominio vencido | `ImageUploader.tsx` | Actualizar a un correo válido |
| 16 | Pendiente: **sin CI** (no hay `.github/workflows/`); la suite pytest existe pero nada la corre automáticamente | repo | Sin red de seguridad automática |

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
