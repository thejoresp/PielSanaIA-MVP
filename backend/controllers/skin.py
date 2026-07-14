from fastapi import APIRouter, Request, File, UploadFile, HTTPException
from openai import OpenAI
import base64
import os
import re
import json
from io import BytesIO
from PIL import Image
from pydantic import BaseModel

# Importar el servicio de análisis de piel
from backend.services.skin_analysis_service import predict_lunares_class, predict_acne_class, predict_rosacea_class
from backend.models.condition import ConditionInfo

# Configurar el router
router = APIRouter()

# Crear un nuevo router para OpenAI
openai_router = APIRouter()

# Límite de tamaño de imagen para evitar abusos y controlar costos (CPU / OpenAI).
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


async def leer_imagen_validada(file: UploadFile) -> bytes:
    """Valida tipo, tamaño y que sea una imagen decodificable; devuelve los bytes.

    Lanza HTTPException (400/413) ante entradas inválidas. Colocar la llamada
    fuera de los try/except de los endpoints para que la excepción propague.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
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
        Image.open(BytesIO(image_bytes)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.")
    return image_bytes


async def analizar_con_modelo(file: UploadFile, predict_fn) -> dict:
    """Valida la imagen, ejecuta el modelo indicado y arma la respuesta estándar.

    Centraliza el flujo común de los endpoints de clasificación (lunares, acné,
    rosácea) para no repetir validación, manejo de errores y forma de respuesta.
    """
    image_bytes = await leer_imagen_validada(file)
    try:
        pred_label, probabilities = predict_fn(image_bytes)
    except Exception as e:
        print(f"Error analizando la imagen: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al analizar la imagen: {str(e)}")
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


def _completar_chat(api_key: str, base_url, model: str, messages: list) -> str:
    """Ejecuta un chat.completions contra un proveedor compatible con OpenAI.

    Maneja los dos fallos frecuentes: falta de API key (503) y error de red/servicio (502).
    """
    if not api_key:
        raise HTTPException(status_code=503, detail="El servicio de análisis con IA no está configurado.")
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(model=model, messages=messages, max_tokens=500)
    except Exception as e:
        print(f"Error llamando al proveedor de IA ({model}): {e}")
        raise HTTPException(status_code=502, detail="No se pudo contactar al servicio de análisis. Intenta nuevamente.")
    return response.choices[0].message.content


def llamar_deepseek(messages: list) -> str:
    """Texto vía DeepSeek (descripción / recomendaciones)."""
    return _completar_chat(os.getenv("DEEPSEEK_API_KEY"), DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, messages)


def llamar_openai_vision(messages: list) -> str:
    """Visión vía OpenAI gpt-4o (DeepSeek no soporta imágenes por API). Opcional."""
    return _completar_chat(os.getenv("OPENAI_API_KEY"), None, OPENAI_VISION_MODEL, messages)

# Diccionario de condiciones (temporal, normalmente iría en un archivo aparte)
conditions_data = {
    "rosacea": ConditionInfo(
        name="rosacea",
        title="Rosácea",
        description="La rosácea es una afección crónica que causa enrojecimiento y vasos sanguíneos visibles en la cara, a veces con pequeños bultos rojos llenos de pus.",
        causes=[
            'Predisposición genética',
            'Problemas con los vasos sanguíneos faciales',
            'Ácaros microscópicos (Demodex)',
            'Bacterias intestinales (H. pylori)',
            'Desencadenantes ambientales'
        ],
        symptoms=[
            'Enrojecimiento persistente en el centro de la cara',
            'Vasos sanguíneos dilatados visibles',
            'Bultos rojos (pápulas) y pústulas',
            'Sensación de ardor o escozor',
            'Piel sensible y reactiva',
            'Engrosamiento de la piel nasal (rinofima)'
        ],
        treatment=[
            'Medicamentos tópicos (metronidazol, ácido azelaico)',
            'Antibióticos orales',
            'Isotretinoína (casos severos)',
            'Terapias con láser o luz pulsada',
            'Evitar desencadenantes conocidos'
        ],
        prevention=[
            'Usar protector solar diariamente',
            'Evitar extremos de temperatura',
            'Evitar alimentos y bebidas desencadenantes',
            'Usar productos para piel sensible',
            'Mantener una buena rutina de cuidado facial'
        ],
        image='https://images.pexels.com/photos/1138531/pexels-photo-1138531.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1'
    ),
    "acne": ConditionInfo(
        name="acne",
        title="Acné",
        description="El acné es una condición común que ocurre cuando los folículos pilosos se obstruyen con grasa y células muertas de la piel, causando granos y espinillas.",
        causes=[
            'Cambios hormonales',
            'Exceso de producción de grasa (sebo)',
            'Bacterias',
            'Ciertos medicamentos',
            'Estrés'
        ],
        symptoms=[
            'Puntos negros y blancos',
            'Espinillas',
            'Protuberancias rojas y dolorosas',
            'Quistes',
            'Cicatrices'
        ],
        treatment=[
            'Limpieza suave de la piel',
            'Medicamentos tópicos (peróxido de benzoilo, retinoides)',
            'Antibióticos',
            'Terapias hormonales',
            'Evitar manipular las lesiones'
        ],
        prevention=[
            'Lavar el rostro regularmente',
            'Evitar productos grasos',
            'No exprimir los granos',
            'Mantener el cabello limpio',
            'Usar protector solar no comedogénico'
        ],
        image='https://images.pexels.com/photos/10004287/pexels-photo-10004287.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1'
    ),
    "manchas": ConditionInfo(
        name="manchas",
        title="Manchas Solares",
        description="Las manchas solares son áreas de la piel que se oscurecen debido a la exposición prolongada al sol, también conocidas como lentigos solares.",
        causes=[
            'Exposición excesiva a la radiación UV',
            'Envejecimiento de la piel',
            'Predisposición genética'
        ],
        symptoms=[
            'Manchas planas y marrones',
            'Aparición en zonas expuestas al sol',
            'No suelen causar dolor ni molestias'
        ],
        treatment=[
            'Cremas despigmentantes',
            'Tratamientos con láser',
            'Peelings químicos',
            'Crioterapia',
            'Protección solar diaria'
        ],
        prevention=[
            'Evitar la exposición solar prolongada',
            'Usar protector solar de amplio espectro',
            'Utilizar ropa protectora',
            'Evitar camas solares',
            'Revisar la piel regularmente'
        ],
        image='https://images.pexels.com/photos/7479603/pexels-photo-7479603.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1'
    ),
    "lunares": ConditionInfo(
        name="lunares",
        title="Lunares",
        description="Los lunares son áreas pequeñas de pigmentación en la piel, generalmente inofensivas, pero algunos pueden evolucionar y requerir control dermatológico.",
        causes=[
            'Acumulación de melanocitos',
            'Factores genéticos',
            'Exposición solar'
        ],
        symptoms=[
            'Pequeñas manchas marrones o negras',
            'Pueden ser planas o elevadas',
            'Cambios en el color, tamaño o forma pueden ser signo de alerta'
        ],
        treatment=[
            'Observación regular',
            'Extirpación quirúrgica si es necesario',
            'Biopsia en caso de sospecha de malignidad',
            'Evitar la exposición solar excesiva',
            'Consulta dermatológica ante cambios sospechosos'
        ],
        prevention=[
            'Usar protector solar',
            'Evitar la exposición solar intensa',
            'Autoexamen de la piel',
            'Consultar al dermatólogo ante cambios',
            'No manipular los lunares'
        ],
        image='https://images.pexels.com/photos/8058606/pexels-photo-8058606.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1'
    ),
}

class PrediccionRequest(BaseModel):
    prediccion: str

@router.get("/")
async def get_upload_page(request: Request):
    """Sirve la página principal para cargar imágenes."""
    raise HTTPException(status_code=404, detail="No implementado: la vista HTML es manejada por el frontend.")

@router.post("/upload")
async def handle_image_upload(request: Request, file: UploadFile = File(...)):
    image_bytes = await leer_imagen_validada(file)
    try:
        pred_label, probabilities = predict_lunares_class(image_bytes)
        if pred_label is not None:
            print(f"Predicción para {file.filename}: {pred_label}")
        else:
            print(f"No se pudo predecir la clase para {file.filename}.")
            raise HTTPException(status_code=500, detail="Error al procesar la imagen: No se pudo predecir la clase.")
        return {"filename": file.filename, "prediccion": pred_label, "probabilidades": probabilities}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error crítico al procesar la imagen: {e}")
        raise HTTPException(status_code=500, detail=f"Error crítico al procesar la imagen: {str(e)}")

@router.get("/results")
async def get_results_page(request: Request, image_name: str = None, analysis_status: str = None):
    """Sirve la página de resultados."""
    raise HTTPException(status_code=404, detail="No implementado: la vista HTML es manejada por el frontend.")

@router.post("/api/analyze", tags=["Skin Analysis API"])
async def api_analyze_skin(file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_lunares_class)

@router.post("/api/analyze-lunares", tags=["Skin Analysis API"])
async def api_analyze_lunares(file: UploadFile = File(...)):
    """Endpoint API para analizar una imagen solo con el modelo lunares.keras."""
    return await analizar_con_modelo(file, predict_lunares_class)

@router.get("/api/condition/{condition_name}", response_model=ConditionInfo, tags=["Skin Info"])
async def get_condition_info(condition_name: str):
    condition = conditions_data.get(condition_name.lower())
    if not condition:
        raise HTTPException(status_code=404, detail="Condición no encontrada")
    return condition

@router.post("/api/analyze-acne", tags=["Skin Analysis API"])
async def api_analyze_acne(file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_acne_class)

@router.post("/api/analyze-rosacea", tags=["Skin Analysis API"])
async def api_analyze_rosacea(file: UploadFile = File(...)):
    return await analizar_con_modelo(file, predict_rosacea_class)

@openai_router.post("/openai-analizar")
async def analizar_imagen_openai(file: UploadFile = File(...)):
    image_bytes = await leer_imagen_validada(file)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:{file.content_type};base64,{image_base64}"

    prompt = (
        "Analiza la imagen de piel que te envío. "
        "Dime qué tipo de afección ves (acné, lunares, rosácea, mancha solar, etc.). Que inicie con mayúscula. "
        "Dame una breve descripción educativa de la afección detectada. "
        "Dame también 5 recomendaciones para esa afección. "
        "Responde en formato JSON con los campos 'afeccion', 'descripcion' y 'recomendaciones' (lista de strings)."
    )

    content = llamar_openai_vision([
        {"role": "system", "content": "Eres un dermatólogo experto."},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_data_url}}
        ]}
    ])

    # Limpia los bloques de código si existen
    content = re.sub(r"^```json|^```|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        resultado = json.loads(content)
    except Exception:
        resultado = {
            "afeccion": "No se pudo analizar",
            "recomendaciones": ["Intenta con otra imagen o consulta a un dermatólogo."]
        }
    return resultado

@openai_router.post("/openai-recomendaciones")
async def obtener_recomendaciones_openai(request: PrediccionRequest):
    prediccion = request.prediccion
    prompt = (
        f"Tengo un paciente con la siguiente condición dermatológica: '{prediccion}'. "
        "Dame una breve descripción educativa de la condición detectada y 5 recomendaciones para el paciente. "
        "Responde en formato JSON con los campos 'descripcion' (string) y 'recomendaciones' (lista de strings)."
    )
    content = llamar_deepseek([
        {"role": "system", "content": "Eres un dermatólogo experto."},
        {"role": "user", "content": prompt}
    ])
    content = re.sub(r"^```json|^```|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        resultado = json.loads(content)
    except Exception:
        resultado = {"descripcion": "No se pudo generar la descripción.", "recomendaciones": ["No se pudieron generar recomendaciones. Intenta nuevamente."]}
    return resultado

# Registrar el router de OpenAI en el router principal
router.include_router(openai_router) 