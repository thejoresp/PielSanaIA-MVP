from fastapi import APIRouter, Request, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from openai import OpenAI
import base64
import json
import logging
import os
import re
from io import BytesIO
from PIL import Image
from pydantic import BaseModel, validator

# Importar el servicio de análisis de piel
from backend.services.skin_analysis_service import (
    predict_lunares_class,
    predict_acne_class,
    predict_rosacea_class,
    LUNARES_CLASS_LABELS,
    ACNE_CLASS_LABELS,
    ROSACEA_CLASS_LABELS,
)
from backend.config.rate_limit import limiter, LIMITE_ANALISIS, LIMITE_IA

logger = logging.getLogger(__name__)

# Configurar el router
router = APIRouter()

# Crear un nuevo router para OpenAI
openai_router = APIRouter()

# Límite de tamaño de imagen para evitar abusos y controlar costos (CPU / OpenAI).
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

# Límite de resolución: el de bytes NO alcanza. Un PNG de un color sólido de
# 13000x13000 pesa unos cientos de KB (pasa el filtro de 8 MB) pero al decodificarlo
# `img_to_array` produce un array float32 de ~2 GB y tumba el contenedor por OOM.
# Pillow por su cuenta recién corta cerca de los 179M de píxeles (y solo avisa a los 89M).
MAX_IMAGE_PIXELS = 40_000_000  # 40 MP: holgado para cualquier cámara de celular

# Formatos aceptados. El `content_type` lo elige el cliente en el header multipart,
# así que la allowlist evita además que un valor arbitrario termine interpolado en
# el data URL que se manda al proveedor de visión (ver `analizar_imagen_openai`).
CONTENT_TYPES_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}


async def leer_imagen_validada(file: UploadFile) -> bytes:
    """Valida tipo, tamaño, resolución y que sea una imagen decodificable.

    Devuelve los bytes. Lanza HTTPException (400/413) ante entradas inválidas.
    Colocar la llamada fuera de los try/except de los endpoints para que la
    excepción propague.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in CONTENT_TYPES_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen JPEG, PNG o WebP.",
        )
    # Lee en fragmentos y corta apenas se supera el límite, para no cargar en
    # memoria (ni spoolear a disco) una subida gigante antes de rechazarla.
    buffer = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="La imagen supera el tamaño máximo permitido (8 MB).",
            )
    if not buffer:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")
    image_bytes = bytes(buffer)
    try:
        # `Image.open` solo lee las cabeceras, así que `size` está disponible sin
        # decodificar. `verify()` invalida el objeto: no reutilizarlo después.
        with Image.open(BytesIO(image_bytes)) as probe:
            ancho, alto = probe.size
            probe.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.")
    # Fuera del try: si no, el HTTPException lo comería el `except Exception`.
    if ancho * alto > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=413,
            detail="La imagen tiene una resolución excesiva (máximo 40 megapíxeles).",
        )
    return image_bytes


async def analizar_con_modelo(file: UploadFile, predict_fn) -> dict:
    """Valida la imagen, ejecuta el modelo indicado y arma la respuesta estándar.

    Centraliza el flujo común de los endpoints de clasificación (lunares, acné,
    rosácea) para no repetir validación, manejo de errores y forma de respuesta.
    """
    image_bytes = await leer_imagen_validada(file)
    try:
        # `predict_fn` es CPU-bound (model.predict). Ejecutarlo directo dentro de una
        # corrutina congela el event loop entero mientras dura la inferencia: el resto
        # de los requests, health checks incluidos, quedan esperando.
        pred_label, probabilities = await run_in_threadpool(predict_fn, image_bytes)
    except Exception:
        # El detalle va al log, no al cliente: `str(e)` de TensorFlow expone rutas del
        # filesystem y versiones de librerías.
        logger.exception("Error analizando la imagen.")
        raise HTTPException(status_code=500, detail="Error interno del servidor al analizar la imagen.")
    if pred_label is None:
        raise HTTPException(status_code=500, detail="No se pudo predecir la clase para la imagen.")
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "prediccion": pred_label,
        "probabilidades": probabilities,
    }


# Proveedores de IA (ambos con API compatible con OpenAI):
# - Texto (descripción / recomendaciones): DeepSeek. Requiere DEEPSEEK_API_KEY.
# - Visión (detección desde la imagen): OpenAI gpt-4o, porque la API de DeepSeek NO
#   acepta imágenes. Este flujo es OPCIONAL: sin OPENAI_API_KEY responde 503 y el
#   resto de la app sigue funcionando solo con DeepSeek.
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

# Un proveedor lento no debe retener un worker indefinidamente.
TIMEOUT_IA = 30
# Una descripción más 5 recomendaciones en español no entran en 500 tokens: si la
# respuesta se corta, el JSON queda inválido y el usuario ve el mensaje de fallback.
MAX_TOKENS_IA = 900


def _completar_chat(api_key: str, base_url, model: str, messages: list) -> str:
    """Ejecuta un chat.completions contra un proveedor compatible con OpenAI.

    Maneja los dos fallos frecuentes: falta de API key (503) y error de red/servicio (502).
    """
    if not api_key:
        raise HTTPException(status_code=503, detail="El servicio de análisis con IA no está configurado.")
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=TIMEOUT_IA)
        response = client.chat.completions.create(model=model, messages=messages, max_tokens=MAX_TOKENS_IA)
    except Exception:
        logger.exception("Error llamando al proveedor de IA (%s).", model)
        raise HTTPException(status_code=502, detail="No se pudo contactar al servicio de análisis. Intenta nuevamente.")
    if not response.choices:
        logger.error("El proveedor de IA (%s) devolvió una respuesta sin opciones.", model)
        raise HTTPException(status_code=502, detail="El servicio de análisis devolvió una respuesta vacía.")
    return response.choices[0].message.content or ""


def llamar_deepseek(messages: list) -> str:
    """Texto vía DeepSeek (descripción / recomendaciones)."""
    return _completar_chat(os.getenv("DEEPSEEK_API_KEY"), DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, messages)


def llamar_openai_vision(messages: list) -> str:
    """Visión vía OpenAI gpt-4o (DeepSeek no soporta imágenes por API). Opcional."""
    return _completar_chat(os.getenv("OPENAI_API_KEY"), None, OPENAI_VISION_MODEL, messages)


# Rol compartido por ambos proveedores.
SYSTEM_DERMATOLOGO = "Eres un dermatólogo experto."

# Los proveedores a veces envuelven el JSON en un bloque ```json ... ```.
_BLOQUE_CODIGO = re.compile(r"^```json|^```|```$", flags=re.MULTILINE)


def _parsear_json_ia(content: str, respaldo: dict) -> dict:
    """Convierte la respuesta del proveedor en dict, con un respaldo si no es JSON válido.

    Se devuelve el respaldo en vez de un error para que la página de resultados siga
    mostrando la predicción del modelo local aunque la IA falle.
    """
    limpio = _BLOQUE_CODIGO.sub("", content.strip()).strip()
    try:
        return json.loads(limpio)
    except ValueError:
        logger.warning("El proveedor de IA no devolvió JSON válido; se usa el respaldo.")
        return respaldo

# Las 11 etiquetas que pueden salir de los modelos. El frontend solo manda una de
# estas (`analysis.prediccion`), así que la allowlist no restringe ningún uso real.
ETIQUETAS_VALIDAS = frozenset(
    list(LUNARES_CLASS_LABELS.values())
    + list(ACNE_CLASS_LABELS.values())
    + list(ROSACEA_CLASS_LABELS.values())
)


class PrediccionRequest(BaseModel):
    prediccion: str

    @validator("prediccion")
    def validar_etiqueta(cls, valor):
        """Evita que texto arbitrario llegue al prompt del proveedor de IA.

        Sin esto, `prediccion` se interpola tal cual en el prompt: cualquiera puede
        mandar instrucciones ("ignorá lo anterior y...") o un texto enorme, y los
        tokens los paga el proyecto.
        """
        if valor not in ETIQUETAS_VALIDAS:
            raise ValueError("Predicción desconocida.")
        return valor

# Este controlador expone solo JSON. Las vistas HTML (`/skin/`, `/skin/results`) y el
# endpoint `/skin/upload` se eliminaron: las primeras eran stubs que siempre daban 404
# y el último duplicaba `/api/analyze` sin que nadie lo llamara.

@router.post("/api/analyze", tags=["Skin Analysis API"])
@limiter.limit(LIMITE_ANALISIS)
async def api_analyze_skin(request: Request, file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_lunares_class)

@router.post("/api/analyze-lunares", tags=["Skin Analysis API"])
@limiter.limit(LIMITE_ANALISIS)
async def api_analyze_lunares(request: Request, file: UploadFile = File(...)):
    """Endpoint API para analizar una imagen solo con el modelo lunares.keras."""
    return await analizar_con_modelo(file, predict_lunares_class)

@router.post("/api/analyze-acne", tags=["Skin Analysis API"])
@limiter.limit(LIMITE_ANALISIS)
async def api_analyze_acne(request: Request, file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_acne_class)

@router.post("/api/analyze-rosacea", tags=["Skin Analysis API"])
@limiter.limit(LIMITE_ANALISIS)
async def api_analyze_rosacea(request: Request, file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_rosacea_class)

@openai_router.post("/openai-analizar")
@limiter.limit(LIMITE_IA)
async def analizar_imagen_openai(request: Request, file: UploadFile = File(...)):
    image_bytes = await leer_imagen_validada(file)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    # Normalizado y ya validado contra CONTENT_TYPES_PERMITIDOS: nunca interpolar
    # `file.content_type` crudo, que lo controla el cliente.
    content_type = file.content_type.split(";")[0].strip().lower()
    image_data_url = f"data:{content_type};base64,{image_base64}"

    prompt = (
        "Analiza la imagen de piel que te envío. "
        "Dime qué tipo de afección ves (acné, lunares, rosácea, mancha solar, etc.). Que inicie con mayúscula. "
        "Dame una breve descripción educativa de la afección detectada. "
        "Dame también 5 recomendaciones para esa afección. "
        "Responde en formato JSON con los campos 'afeccion', 'descripcion' y 'recomendaciones' (lista de strings)."
    )

    # El cliente de OpenAI es síncrono: sin threadpool bloquearía el event loop
    # durante toda la llamada (varios segundos).
    content = await run_in_threadpool(llamar_openai_vision, [
        {"role": "system", "content": SYSTEM_DERMATOLOGO},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_data_url}}
        ]}
    ])

    return _parsear_json_ia(content, respaldo={
        "afeccion": "No se pudo analizar",
        "recomendaciones": ["Intenta con otra imagen o consulta a un dermatólogo."],
    })

@openai_router.post("/openai-recomendaciones")
@limiter.limit(LIMITE_IA)
# `request: Request` es obligatorio para slowapi; el body pasa a llamarse `datos`.
async def obtener_recomendaciones_openai(request: Request, datos: PrediccionRequest):
    prediccion = datos.prediccion
    prompt = (
        f"Tengo un paciente con la siguiente condición dermatológica: '{prediccion}'. "
        "Dame una breve descripción educativa de la condición detectada y 5 recomendaciones para el paciente. "
        "Responde en formato JSON con los campos 'descripcion' (string) y 'recomendaciones' (lista de strings)."
    )
    content = await run_in_threadpool(llamar_deepseek, [
        {"role": "system", "content": SYSTEM_DERMATOLOGO},
        {"role": "user", "content": prompt}
    ])
    return _parsear_json_ia(content, respaldo={
        "descripcion": "No se pudo generar la descripción.",
        "recomendaciones": ["No se pudieron generar recomendaciones. Intenta nuevamente."],
    })

# Registrar el router de OpenAI en el router principal
router.include_router(openai_router)
