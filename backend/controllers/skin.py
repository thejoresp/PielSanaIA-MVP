from fastapi import APIRouter, Request, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from pathlib import Path
import asyncio
import uuid
import openai
import base64
import os
import re
import json
from pydantic import BaseModel

# Importar el servicio de análisis de piel
from backend.services.skin_analysis_service import predict_lunares_class, predict_acne_class, predict_rosacea_class
from backend.models.condition import ConditionInfo

# Configurar el router
router = APIRouter()

# Crear un nuevo router para OpenAI
openai_router = APIRouter()

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

# Almacenamiento en memoria para resultados de lunares
lunares_results = {}

class PrediccionRequest(BaseModel):
    prediccion: str

@router.get("/")
async def get_upload_page(request: Request):
    """Sirve la página principal para cargar imágenes."""
    raise HTTPException(status_code=404, detail="No implementado: la vista HTML es manejada por el frontend.")

@router.post("/upload")
async def handle_image_upload(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    try:
        image_bytes = await file.read()
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
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    try:
        image_bytes = await file.read()
        pred_label, probabilities = predict_lunares_class(image_bytes)
        if pred_label is not None:
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "prediccion": pred_label,
                "probabilidades": probabilities
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudo predecir la clase para la imagen.")
    except Exception as e:
        print(f"Error en API /api/analyze: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al analizar la imagen: {str(e)}")

@router.post("/api/analyze-lunares", tags=["Skin Analysis API"])
async def api_analyze_lunares(file: UploadFile = File(...)):
    """Endpoint API para analizar una imagen solo con el modelo lunares.keras."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    try:
        image_bytes = await file.read()
        pred_label, probabilities = predict_lunares_class(image_bytes)
        if pred_label is not None:
            result_id = str(uuid.uuid4())
            lunares_results[result_id] = {
                "filename": file.filename,
                "content_type": file.content_type,
                "prediccion": pred_label,
                "probabilidades": probabilities
            }
            return {"id": result_id}
        else:
            raise HTTPException(status_code=500, detail="No se pudo predecir la clase para la imagen.")
    except Exception as e:
        print(f"Error en API /api/analyze-lunares: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al analizar la imagen: {str(e)}")

@router.get("/api/analyze-lunares/{result_id}", tags=["Skin Analysis API"])
async def get_lunares_result(result_id: str):
    """Obtener el resultado del análisis de lunares por ID."""
    result = lunares_results.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    return result

@router.get("/api/condition/{condition_name}", response_model=ConditionInfo, tags=["Skin Info"])
async def get_condition_info(condition_name: str):
    condition = conditions_data.get(condition_name.lower())
    if not condition:
        raise HTTPException(status_code=404, detail="Condición no encontrada")
    return condition

@router.post("/api/analyze-acne", tags=["Skin Analysis API"])
async def api_analyze_acne(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    try:
        image_bytes = await file.read()
        pred_label, probabilities = predict_acne_class(image_bytes)
        if pred_label is not None:
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "prediccion": pred_label,
                "probabilidades": probabilities
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudo predecir la clase para la imagen.")
    except Exception as e:
        print(f"Error en API /api/analyze-acne: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al analizar la imagen: {str(e)}")

@router.post("/api/analyze-rosacea", tags=["Skin Analysis API"])
async def api_analyze_rosacea(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
    try:
        image_bytes = await file.read()
        pred_label, probabilities = predict_rosacea_class(image_bytes)
        if pred_label is not None:
            return {
                "filename": file.filename,
                "content_type": file.content_type,
                "prediccion": pred_label,
                "probabilidades": probabilities
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudo predecir la clase para la imagen.")
    except Exception as e:
        print(f"Error en API /api/analyze-rosacea: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al analizar la imagen: {str(e)}")

@openai_router.post("/openai-analizar")
async def analizar_imagen_openai(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:{file.content_type};base64,{image_base64}"

    prompt = (
        "Analiza la imagen de piel que te envío. "
        "Dime qué tipo de afección ves (acné, lunares, rosácea, mancha solar, etc.). Que inicie con mayusculash "
        "Dame una breve descripción educativa de la afección detectada. "
        "Dame también 5 recomendaciones para esa afección. "
        "Responde en formato JSON con los campos 'afeccion', 'descripcion' y 'recomendaciones' (lista de strings)."
    )

    openai_api_key = os.getenv("OPENAI_API_KEY")
    print("API KEY:", openai_api_key)
    print("Tamaño de la imagen:", len(image_bytes))
    openai.api_key = openai_api_key
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un dermatólogo experto."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]}
        ],
        max_tokens=500
    )
    print("Respuesta de OpenAI:", response.choices[0].message.content)

    content = response.choices[0].message.content
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
    import openai
    import os
    import json
    import re
    prediccion = request.prediccion
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai.api_key = openai_api_key
    prompt = (
        f"Tengo un paciente con la siguiente condición dermatológica: '{prediccion}'. "
        "Dame una breve descripción educativa de la condición detectada y 5 recomendaciones para el paciente. "
        "Responde en formato JSON con los campos 'descripcion' (string) y 'recomendaciones' (lista de strings)."
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un dermatólogo experto."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    content = response.choices[0].message.content
    content = re.sub(r"^```json|^```|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        resultado = json.loads(content)
    except Exception:
        resultado = {"descripcion": "No se pudo generar la descripción.", "recomendaciones": ["No se pudieron generar recomendaciones. Intenta nuevamente."]}
    return resultado

# Registrar el router de OpenAI en el router principal
router.include_router(openai_router) 