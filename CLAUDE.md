# PielSana IA — Guía para el agente

MVP de análisis de piel por IA. El usuario sube una foto y recibe una clasificación de
condiciones cutáneas (lunares/HAM10000, acné, rosácea) generada por modelos locales Keras,
enriquecida con explicaciones y recomendaciones vía OpenAI.

> **Contexto clínico:** es una herramienta educativa/de autocuidado, **no** un diagnóstico
> médico. Todo texto orientado al usuario debe recordar que no sustituye a un dermatólogo.

## Arquitectura

Monorepo con dos servicios independientes:

- **`backend/`** — API REST con **FastAPI** (Python 3.10).
  - `main.py` — instancia FastAPI, CORS abierto (`allow_origins=["*"]`), monta `skin.router` bajo `/skin`.
  - `controllers/skin.py` — endpoints de análisis + router de OpenAI. Datos de condiciones embebidos en `conditions_data`.
  - `services/skin_analysis_service.py` — carga perezosa de los modelos `.keras` y predicción. Cada modelo se cachea en una global.
  - `config/model_config.py` — rutas de modelos (override por env), fuerza CPU en TensorFlow.
  - `models/condition.py` — modelo Pydantic `ConditionInfo`.
  - Modelos: `backend/modelos/ham10000/lunares.keras`, `backend/modelos/acne/acne.keras`, `backend/modelos/rosacea/rosacea.keras` (no versionados en git).
- **`frontend/`** — SPA con **React 18 + TypeScript + Vite + Tailwind**, ruteo con `react-router-dom`.
  - Páginas en `src/pages/`, componentes en `src/components/`. Una página de resultados por modelo (`ResultsLunares`, `ResultsAcne`, `ResultsRosacea`, `ResultsOpenAI`).

Frontend y backend se comunican por HTTP; el backend no sirve HTML (las vistas HTML devuelven 404 a propósito).

## Comandos

### Backend
```bash
# Dependencias
pip install -r backend/requirements.txt

# Desarrollo (desde la raíz del repo — el paquete es backend.main)
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

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

- `POST /skin/api/analyze` y `POST /skin/api/analyze-lunares` — clasificación de lunares (7 clases HAM10000). `analyze-lunares` guarda el resultado en memoria y devuelve un `id` recuperable con `GET /skin/api/analyze-lunares/{id}`.
- `POST /skin/api/analyze-acne` — clasificación binaria de acné (sigmoide).
- `POST /skin/api/analyze-rosacea` — clasificación binaria de rosácea (sigmoide).
- `GET  /skin/api/condition/{nombre}` — info estática de una condición (`rosacea`, `acne`, `manchas`, `lunares`).
- `POST /skin/openai-analizar` — envía la imagen a OpenAI (`gpt-4o`) y devuelve JSON `{afeccion, descripcion, recomendaciones}`.
- `POST /skin/openai-recomendaciones` — dada una predicción, devuelve `{descripcion, recomendaciones}` vía OpenAI.

## Variables de entorno

**Backend** (`.env` en la raíz, no commitear):
- `OPENAI_API_KEY` — requerida para los endpoints de OpenAI.
- `LUNARES_MODEL_PATH`, `ACNE_MODEL_PATH`, `ROSACEA_MODEL_PATH` — rutas de los `.keras` (tienen default).

**Frontend** (`frontend/.env`, en build time — Vite):
- `VITE_API_URL` — URL base del backend. TODO el frontend llama a `${VITE_API_URL}/skin/...`.
  Si falta, las peticiones apuntan a `undefined/skin/...` y fallan. Debe definirse **antes** de `npm run build`.

## Despliegue

Topología actual:
- **Backend:** instancia **EC2 Ubuntu 22.04** (`t2.micro`) en AWS, IP `54.82.199.243`. Se provisiona con
  `infra.sh` (crea VPC, subred, IGW, security group con puertos 22/53/80/8080, EC2 + IP elástica). El
  user-data (`dockerUbuntu.txt`) instala Docker. Se despliega construyendo la imagen del `backend/Dockerfile`
  y corriendo el contenedor en el puerto `8080` (`reboot_backend.sh`). `nginx_manager.sh` gestiona Nginx
  como reverse proxy. Acceso por SSH con `connect_aws.sh` (usa `vockey.pem`).
- **Frontend:** build estático de Vite publicado con **`npm run deploy`** (gh-pages → GitHub Pages).

### ⚠️ Puntos críticos de despliegue
1. **Mixed content:** el frontend en GitHub Pages se sirve por **HTTPS**, pero el backend EC2 responde por
   **HTTP** (`http://54.82.199.243:8080`). El navegador **bloquea** llamadas HTTPS→HTTP. Hay que poner el
   backend detrás de HTTPS (Nginx + certificado, o un dominio con TLS) y apuntar `VITE_API_URL` a esa URL https.
2. **Versión de Python:** producción usa `python:3.10-slim` (Dockerfile). El `requirements.txt` fija
   `tensorflow==2.19.0`, que **no tiene wheels para Python ≥3.13** (solo 2.20+). Para desarrollo local usar
   Python 3.10–3.12 (o el propio Docker), no 3.13.
3. **CORS abierto:** `main.py` usa `allow_origins=["*"]`. Restringir al dominio del frontend en producción.
4. **Modelos `.keras` ausentes del repo** (gitignored). Sin ellos el backend responde 500 en los endpoints de
   predicción; hay que copiarlos a `backend/modelos/{ham10000,acne,rosacea}/` en el servidor.
5. **`OPENAI_API_KEY` no debe imprimirse.** Hoy `controllers/skin.py` hace `print` de la key — quitarlo.
6. **Estado en memoria:** `lunares_results` es un dict en memoria; no sobrevive reinicios ni escala a varias
   instancias. Persistir (Redis/DB) si se escala.

## Convenciones y cuidados

- **Preprocesado de imágenes uniforme:** RGB → resize `224x224` → normalizar `/255.0` → shape `(1,224,224,3)`. Respetar esto al añadir modelos.
- Los modelos se cargan de forma perezosa y se cachean en globales; si un modelo no carga, las funciones devuelven `(None, None)` y el endpoint responde 500. No romper ese contrato.
- Salidas: lunares es multiclase (`argmax`); acné y rosácea son binarias (`> 0.5`). Las probabilidades se devuelven con las etiquetas legibles en español.
- Pydantic está fijado a **1.10.15** (v1) — usar sintaxis Pydantic v1.
- El código, comentarios, labels y mensajes de la API están en **español**; mantener ese idioma.
- No agregar disclaimers médicos de más ni cambiar el tono; PielSana IA insiste en privacidad (las imágenes se procesan de forma temporal y no se almacenan).

## Git

- No añadir el trailer `Co-Authored-By: Claude` en los commits.
