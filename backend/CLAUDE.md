# Backend — convenciones

Contexto general y comandos: [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

## Endpoints (prefijo `/skin`)

- `POST /skin/api/analyze` y `POST /skin/api/analyze-lunares` — clasificación de lunares (7 clases
  HAM10000). Ambos devuelven el resultado completo (`prediccion`, `probabilidades`) directamente; el
  frontend lo pasa entre páginas por `navigate(state)`, igual que acné/rosácea. **No hay estado en
  memoria ni recuperación por `id`.** Si a futuro hace falta persistir resultados, usar Redis/DB, no
  un dict en memoria.
- `POST /skin/api/analyze-acne` — clasificación binaria de acné (sigmoide).
- `POST /skin/api/analyze-rosacea` — clasificación binaria de rosácea (sigmoide).
- `POST /skin/openai-analizar` — envía la imagen a **OpenAI `gpt-4o`** (visión) y devuelve JSON
  `{afeccion, descripcion, recomendaciones}`. Opcional: sin `OPENAI_API_KEY` responde 503. La ruta
  conserva el nombre `openai-*` por compatibilidad con el frontend.
- `POST /skin/openai-recomendaciones` — dada una predicción, devuelve `{descripcion, recomendaciones}`
  vía **DeepSeek** (`deepseek-v4-flash`). La ruta mantiene el nombre `openai-*` aunque el proveedor
  sea DeepSeek. El body **solo acepta una de las 11 etiquetas de los modelos** (`ETIQUETAS_VALIDAS`);
  cualquier otro texto responde 422.

Fuera del prefijo `/skin`:

- `GET /health` — `{status, version, modelos}`, con el estado de carga de cada `.keras`. Es el destino
  para Nginx, el `HEALTHCHECK` de Docker y los monitores de uptime.
- `GET /` — describe la API (ya **no** redirige a `/skin/`, que siempre daba 404).

**Rate limiting:** todos los endpoints de análisis están limitados por IP vía `slowapi`
(`config/rate_limit.py`): `LIMITE_ANALISIS` 20/min en los de modelo, `LIMITE_IA` 10/min en los de IA.
Al agregar un endpoint que consuma CPU o tokens, decorarlo también — y recordar que slowapi **exige**
un parámetro `request: Request` en la firma.

**Validación de subida:** `leer_imagen_validada()` en `controllers/skin.py` valida tipo (allowlist
`CONTENT_TYPES_PERMITIDOS`: jpeg/png/webp), tamaño (8 MB, `MAX_IMAGE_BYTES`), **resolución** (40 MP,
`MAX_IMAGE_PIXELS` — el límite de bytes no frena una bomba de descompresión) y que la imagen sea
decodificable.

## Modelos

- **Preprocesado uniforme:** RGB → resize `224x224` → normalizar `/255.0` → shape `(1,224,224,3)`.
  Respetarlo al añadir modelos.
- **Agregar un modelo** = instanciar un `_ModeloKeras(nombre, ruta)` y un `predict_*_class` que
  delegue en `_clasificar_multiclase` o `_clasificar_binario`. No copiar bloques: esa triplicación ya
  se eliminó una vez.
- Los modelos se cargan de forma perezosa (con lock) y se precargan en el `startup`; si un modelo no
  carga, `predict_*_class` devuelve `(None, None)` y el endpoint responde 500. **No romper ese contrato.**
- Salidas: lunares es multiclase (`argmax`); acné y rosácea son binarias (`> 0.5`). Las probabilidades
  se devuelven con las etiquetas legibles en español.

## Código

- **La inferencia y las llamadas a los proveedores de IA son bloqueantes**: invocarlas siempre con
  `await run_in_threadpool(...)`, nunca directo dentro de una corrutina.
- **Logging, no `print`:** usar `logging.getLogger(__name__)`. Los detalles de excepción van al log
  (`logger.exception`), **nunca** al `detail` de la respuesta: filtran rutas y versiones.
- Pydantic está fijado a **1.10.15** (v1) — usar sintaxis Pydantic v1.
- Producción usa `python:3.10-slim`. `requirements.txt` fija `tensorflow==2.19.0`, que **no tiene
  wheels para Python ≥3.13** (solo 2.20+). Para desarrollo local usar Python 3.10–3.12, no 3.13.
