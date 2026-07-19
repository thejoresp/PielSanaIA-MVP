# PielSana IA — Guía para el agente

MVP de análisis de piel por IA. El usuario sube una foto y recibe una clasificación de
condiciones cutáneas (lunares/HAM10000, acné, rosácea) generada por modelos locales Keras,
enriquecida con explicaciones y recomendaciones vía **DeepSeek** (texto). La detección
automática desde la imagen (endpoint de visión) usa **OpenAI gpt-4o** y es opcional
(DeepSeek no acepta imágenes por API).

> **Contexto clínico:** es una herramienta educativa/de autocuidado, **no** un diagnóstico
> médico. Todo texto orientado al usuario debe recordar que no sustituye a un dermatólogo.

> **Deuda técnica pendiente: [`AUDITORIA.md`](AUDITORIA.md)** — auditoría completa del código
> (2026-07-19) con hallazgos numerados y checkboxes: backend, modelos, frontend, SEO e infra.
> Consultarla antes de encarar mejoras; marcar los ítems al resolverlos.

## Arquitectura

Monorepo con dos servicios independientes:

- **`backend/`** — API REST con **FastAPI** (Python 3.10).
  - `main.py` — instancia FastAPI, configuración de `logging`, CORS por `FRONTEND_ORIGINS`, registro del rate limiter, warmup de modelos en el `startup` y endpoints `GET /` y `GET /health`. Monta `skin.router` bajo `/skin`.
  - `controllers/skin.py` — solo endpoints y validación de entrada; sin datos ni lógica de modelos.
  - `services/skin_analysis_service.py` — clase `_ModeloKeras` (carga perezosa cacheada y **con `threading.Lock`**) + los ayudantes `_clasificar_multiclase` / `_clasificar_binario`. Expone `predict_*_class` y `precargar_modelos()`.
  - `config/model_config.py` — rutas de modelos (override por env), fuerza CPU en TensorFlow.
  - `config/rate_limit.py` — instancia compartida de `slowapi` y los dos límites.
  - Modelos: `backend/modelos/ham10000/lunares.keras`, `backend/modelos/acne/acne.keras`, `backend/modelos/rosacea/rosacea.keras` (no versionados en git).
- **`frontend/`** — SPA con **React 18 + TypeScript + Vite + Tailwind**, ruteo con `react-router-dom`. Organizado por capas:

  | Carpeta | Rol |
  |---|---|
  | `src/api/` | `client.ts` (URL base, `ApiError`, mensajes por código HTTP) y `skin.ts` (una función por endpoint). **Ningún componente hace `fetch` directo.** |
  | `src/types/` | Formas de las respuestas del backend (`AnalisisResultado`, `VisionResultado`…). |
  | `src/data/` | **Contenido estático** que no depende del backend: `condiciones.ts` (las 4 fichas de condiciones). |
  | `src/constants/` | `analisis.ts`: catálogo de tipos de análisis (clave, etiqueta, endpoint, ruta). |
  | `src/hooks/` | `useAnalisisImagen.ts`: todo el estado del flujo de subida y análisis. |
  | `src/components/ui/` | Piezas genéricas (`Spinner`, `BannerError`). |
  | `src/components/upload/` | Flujo de subida: `ImageUploader` (compone), `ConsentModal`, `SelectorTipoAnalisis`, `ZonaDeSubida`, `VistaPreviaImagen`. |
  | `src/components/results/` | `ResultadoLayout` (carcasa visual de las 4 páginas de resultados), `ResultadoModeloLocal` (lunares/acné/rosácea), `SinResultado`. |
  | `src/pages/` | Una por ruta; las de resultados son wrappers de ~7 líneas. |

  - **Agregar un tipo de análisis** = una entrada en `constants/analisis.ts` + su ruta en `App.tsx`. No hay `if/else` por tipo en ningún componente.
  - El **disclaimer médico** vive una sola vez, en `results/ResultadoLayout.tsx`.
  - Las rutas distintas del home se cargan con `React.lazy` (`App.tsx`).

Frontend y backend se comunican por HTTP; el backend **solo devuelve JSON** (no sirve HTML).

## Comandos

### Backend
```bash
# Dependencias
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt   # solo para tests (pytest, httpx)

# Desarrollo (desde la raíz del repo — el paquete es backend.main)
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

# Tests (desde la raíz; los modelos se mockean, no requieren los .keras)
python -m pytest backend/tests

# Docker
sudo docker build -t pielsana-backend -f backend/Dockerfile .
sudo docker run -d --rm --name pielsana-backend -p 8080:8080 pielsana-backend
# ./reboot_backend.sh reconstruye y relanza el contenedor
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # servidor Vite (http://localhost:5173)
npm run build     # build de producción a dist/
npm run lint      # ESLint
npm run deploy    # publica dist/ en GitHub Pages (gh-pages)
```

## Endpoints principales (prefijo `/skin`)

- `POST /skin/api/analyze` y `POST /skin/api/analyze-lunares` — clasificación de lunares (7 clases HAM10000). Ambos devuelven el resultado completo (`prediccion`, `probabilidades`) directamente; el frontend lo pasa entre páginas por `navigate(state)`, igual que acné/rosácea (ya no hay estado en memoria ni recuperación por `id`).
- `POST /skin/api/analyze-acne` — clasificación binaria de acné (sigmoide).
- `POST /skin/api/analyze-rosacea` — clasificación binaria de rosácea (sigmoide).
- `POST /skin/openai-analizar` — envía la imagen a **OpenAI `gpt-4o`** (visión) y devuelve JSON `{afeccion, descripcion, recomendaciones}`. Opcional: sin `OPENAI_API_KEY` responde 503. (La ruta conserva el nombre `openai-*` por compatibilidad con el frontend.)
- `POST /skin/openai-recomendaciones` — dada una predicción, devuelve `{descripcion, recomendaciones}` vía **DeepSeek** (`deepseek-v4-flash`). La ruta mantiene el nombre `openai-*` aunque el proveedor sea DeepSeek. El body **solo acepta una de las 11 etiquetas de los modelos** (`ETIQUETAS_VALIDAS`); cualquier otro texto responde 422.

Fuera del prefijo `/skin`:
- `GET /health` — `{status, version, modelos}`, con el estado de carga de cada `.keras`. Es el destino para Nginx, el `HEALTHCHECK` de Docker y los monitores de uptime.
- `GET /` — describe la API (ya **no** redirige a `/skin/`, que siempre daba 404).

**Rate limiting:** todos los endpoints de análisis están limitados por IP vía `slowapi`
(`backend/config/rate_limit.py`): `LIMITE_ANALISIS` 20/min en los de modelo, `LIMITE_IA` 10/min en
los de IA. Al agregar un endpoint que consuma CPU o tokens, decorarlo también — y recordar que
slowapi **exige** un parámetro `request: Request` en la firma.

## Variables de entorno

> Plantillas de referencia versionadas: **`.env.example`** (raíz, backend) y **`frontend/.env.example`**.
> Copiarlas a `.env` / `frontend/.env` y completar; los `.env` reales no se commitean.

**Backend** (`.env` en la raíz, no commitear):
- `DEEPSEEK_API_KEY` — **requerida** para `/skin/openai-recomendaciones` (texto). API compatible con OpenAI (`base_url https://api.deepseek.com`).
- `DEEPSEEK_MODEL` — opcional, default `deepseek-v4-flash` (`deepseek-chat`/`deepseek-reasoner` se deprecan el 2026/07/24).
- `OPENAI_API_KEY` — **opcional**, solo para `/skin/openai-analizar` (visión gpt-4o). Sin ella ese endpoint responde 503; el resto funciona con DeepSeek.
- `OPENAI_VISION_MODEL` — opcional, default `gpt-4o`.
- `FRONTEND_ORIGINS` — orígenes permitidos por CORS, lista separada por comas. Default: dev local
  (`http://localhost:5173,http://127.0.0.1:5173`). **En producción definirla** con la URL del frontend.
- `LUNARES_MODEL_PATH`, `ACNE_MODEL_PATH`, `ROSACEA_MODEL_PATH` — rutas de los `.keras` (tienen default).
- `LOG_LEVEL` — opcional, default `INFO`. Nivel del `logging` configurado en `main.py`.

**Frontend** (`frontend/.env`, en build time — Vite):
- `VITE_API_URL` — URL base del backend. TODO el frontend llama a `${VITE_API_URL}/skin/...`.
  Si falta, las peticiones apuntan a `undefined/skin/...` y fallan. Debe definirse **antes** de `npm run build`.
- `VITE_BASE` — ruta base del build (`vite.config.ts`). Default `/` (dominio propio / raíz). Para
  GitHub Pages en subruta (`usuario.github.io/REPO`) definir `VITE_BASE="/REPO/"` antes de `npm run build`.

## Despliegue

> **Guía completa (plan actual): [`DESPLIEGUE.md`](DESPLIEGUE.md)** — frontend en Vercel, backend en
> VPS Hetzner con Nginx + DuckDNS + Let's Encrypt (docker-compose/nginx documentados ahí).

Topología actual:
- **Backend:** instancia **EC2 Ubuntu 22.04** (`t2.micro`) en AWS, IP `54.82.199.243`. Se provisiona con
  `infra.sh` (crea VPC, subred, IGW, security group con puertos 22/53/80/8080, EC2 + IP elástica). El
  user-data (`dockerUbuntu.txt`) instala Docker. Se despliega construyendo la imagen del `backend/Dockerfile`
  y corriendo el contenedor en el puerto `8080` (`reboot_backend.sh`). `nginx_manager.sh` gestiona Nginx
  como reverse proxy. Acceso por SSH con `connect_aws.sh` (usa `vockey.pem`).
- **Frontend:** build estático de Vite publicado con **`npm run deploy`** (gh-pages → GitHub Pages).

### ⚠️ Puntos críticos de despliegue
1. **Mixed content + dominio vencido:** el frontend en GitHub Pages se sirve por **HTTPS**, pero el backend EC2
   responde por **HTTP** (`http://54.82.199.243:8080`). El navegador **bloquea** llamadas HTTPS→HTTP. El dominio
   propio (`pielsanaia.click`) **venció** y no se va a renovar; el plan es usar opciones gratis: frontend en
   `https://USUARIO.github.io/PielSanaIA-MVP` y backend en un VPS fijo detrás de HTTPS con **DuckDNS + Let's
   Encrypt** (`https://SUBDOMINIO.duckdns.org`), apuntando `VITE_API_URL` a esa URL https. Ver la memoria del
   proyecto (pendiente-despliegue-vps).
2. **Versión de Python:** producción usa `python:3.10-slim` (Dockerfile). El `requirements.txt` fija
   `tensorflow==2.19.0`, que **no tiene wheels para Python ≥3.13** (solo 2.20+). Para desarrollo local usar
   Python 3.10–3.12 (o el propio Docker), no 3.13.
3. **CORS:** `main.py` lee `FRONTEND_ORIGINS` (default dev local). Definir en producción la URL real del
   frontend; ya **no** usa `allow_origins=["*"]`.
4. **Modelos `.keras` ausentes del repo** (gitignored). Sin ellos el backend responde 500 en los endpoints de
   predicción; hay que copiarlos a `backend/modelos/{ham10000,acne,rosacea}/` en el servidor.
5. **Secretos:** no loguear `DEEPSEEK_API_KEY` ni `OPENAI_API_KEY` (ya se eliminaron los `print` de keys en
   `controllers/skin.py`). El proveedor de texto es DeepSeek; OpenAI solo se usa para el endpoint de visión.
6. **Validación de subida:** `leer_imagen_validada()` en `controllers/skin.py` valida tipo
   (allowlist `CONTENT_TYPES_PERMITIDOS`: jpeg/png/webp), tamaño (8 MB, `MAX_IMAGE_BYTES`),
   **resolución** (40 MP, `MAX_IMAGE_PIXELS` — el límite de bytes no frena una bomba de
   descompresión) y que la imagen sea decodificable.
6b. **Rate limiting detrás del proxy:** `slowapi` limita por IP, pero detrás de Nginx
   `get_remote_address` ve la IP **del proxy** y todos los usuarios comparten el mismo cupo.
   Hay que correr uvicorn con **`--proxy-headers`** y que Nginx envíe `X-Forwarded-For`.
7. **Estado en memoria:** ✅ eliminado — `analyze-lunares` ya no guarda en un dict; devuelve el resultado
   directo (el frontend lo pasa por `navigate(state)`). El backend es ahora sin estado. Si a futuro se
   necesita persistir resultados, usar Redis/DB, no un dict en memoria.
8. **Email de contacto obsoleto:** el modal de consentimiento (`components/upload/ConsentModal.tsx`,
   constante `CONTACTO_DATOS`) apunta a
   `contacto@pielsanaia.click`, que quedó en el dominio **vencido**. Actualizarlo a un correo válido cuando se
   defina el nuevo (p. ej. el email real del proyecto).

## Convenciones y cuidados

- **Preprocesado de imágenes uniforme:** RGB → resize `224x224` → normalizar `/255.0` → shape `(1,224,224,3)`. Respetar esto al añadir modelos.
- **Agregar un modelo** = instanciar un `_ModeloKeras(nombre, ruta)` y un `predict_*_class` que delegue en `_clasificar_multiclase` o `_clasificar_binario`. No copiar bloques: esa triplicación ya se eliminó una vez.
- Los modelos se cargan de forma perezosa (con lock) y se precargan en el `startup`; si un modelo no carga, `predict_*_class` devuelve `(None, None)` y el endpoint responde 500. No romper ese contrato.
- Salidas: lunares es multiclase (`argmax`); acné y rosácea son binarias (`> 0.5`). Las probabilidades se devuelven con las etiquetas legibles en español.
- **La inferencia y las llamadas a los proveedores de IA son bloqueantes**: invocarlas siempre con `await run_in_threadpool(...)`, nunca directo dentro de una corrutina.
- **Logging, no `print`:** usar `logging.getLogger(__name__)`. Los detalles de excepción van al log (`logger.exception`), **nunca** al `detail` de la respuesta: filtran rutas y versiones.
- Pydantic está fijado a **1.10.15** (v1) — usar sintaxis Pydantic v1.

**Frontend**
- **Nunca `fetch` en un componente**: usar `api/skin.ts`. Los errores llegan como `ApiError` con
  un mensaje ya listo para mostrar; renderizarlo con `<BannerError />`, **nunca** con `alert()`.
- **Clases de Tailwind siempre completas.** Interpolarlas (`bg-${color}-100`) no funciona: el purge
  del build las descarta. Por eso los temas de color son mapas de clases enteras.
- **Assets referenciados desde JSX van con `import.meta.env.BASE_URL`**, nunca con ruta absoluta
  (`src="/logo.png"`). Vite reescribe el `index.html` con la `base`, pero **no** las cadenas
  dentro del JSX: con `VITE_BASE` en subruta esas rutas dan 404.
- Todo `useEffect` que haga una petición debe cancelarse en el cleanup (flag `cancelado`).

- El código, comentarios, labels y mensajes de la API están en **español**; mantener ese idioma.
- No agregar disclaimers médicos de más ni cambiar el tono; PielSana IA insiste en privacidad (las imágenes se procesan de forma temporal y no se almacenan).

## Git

- No añadir el trailer `Co-Authored-By: Claude` en los commits.
