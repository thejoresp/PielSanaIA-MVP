"""Carga de los modelos Keras y predicción de condiciones cutáneas.

Los tres modelos comparten estructura, así que la carga perezosa y el armado de la
respuesta viven en `_ModeloKeras` y en los dos ayudantes de predicción; cada modelo
concreto solo declara su ruta y sus etiquetas.

Contrato público (no romper): `predict_*_class(image_bytes)` devuelve
`(etiqueta, probabilidades)` o `(None, None)` si el modelo no está disponible o la
predicción falla. El controlador traduce ese `(None, None)` a un HTTP 500.
"""
import logging
import threading
from io import BytesIO

import tensorflow as tf
from PIL import Image
from tensorflow.keras.preprocessing.image import img_to_array

from backend.config.model_config import LUNARES_MODEL_PATH, ACNE_MODEL_PATH, ROSACEA_MODEL_PATH

logger = logging.getLogger(__name__)


def _preprocesar_imagen(image_bytes: bytes):
    """Preprocesado uniforme: RGB -> resize 224x224 -> /255.0 -> shape (1,224,224,3)."""
    img = Image.open(BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_resized = img.resize((224, 224))
    img_array = img_to_array(img_resized) / 255.0
    return img_array.reshape((1, 224, 224, 3))


class _ModeloKeras:
    """Modelo Keras de carga perezosa, cacheado y seguro entre hilos.

    El candado evita que dos peticiones concurrentes durante el arranque carguen el
    mismo modelo dos veces y dupliquen el pico de RAM (crítico en un VPS de 4 GB con
    tres modelos TensorFlow residentes).
    """

    def __init__(self, nombre: str, ruta: str):
        self._nombre = nombre
        self._ruta = ruta
        self._modelo = None
        self._lock = threading.Lock()

    def _obtener(self):
        if self._modelo is None:
            with self._lock:
                # Doble chequeo: otro hilo pudo cargarlo mientras esperábamos el lock.
                if self._modelo is None:
                    try:
                        logger.info("Cargando modelo %s desde %s...", self._nombre, self._ruta)
                        self._modelo = tf.keras.models.load_model(self._ruta)
                        logger.info("Modelo %s cargado exitosamente.", self._nombre)
                    except Exception:
                        logger.exception("Error cargando el modelo %s.", self._nombre)
        return self._modelo

    def predecir(self, image_bytes: bytes):
        """Devuelve el array de predicciones, o None si el modelo no está disponible."""
        modelo = self._obtener()
        if modelo is None:
            logger.error("El modelo %s no está cargado.", self._nombre)
            return None
        try:
            return modelo.predict(_preprocesar_imagen(image_bytes))
        except Exception:
            logger.exception("Error al predecir con el modelo %s.", self._nombre)
            return None

    def cargar(self):
        """Fuerza la carga (warmup al arrancar). Devuelve True si quedó disponible."""
        return self._obtener() is not None


def _clasificar_multiclase(modelo: _ModeloKeras, image_bytes: bytes, etiquetas: list):
    """Salida softmax: gana el índice con mayor probabilidad."""
    preds = modelo.predecir(image_bytes)
    if preds is None:
        return None, None
    probabilidades = {etiqueta: float(preds[0][i]) for i, etiqueta in enumerate(etiquetas)}
    return etiquetas[preds.argmax(axis=1)[0]], probabilidades


def _clasificar_binario(modelo: _ModeloKeras, image_bytes: bytes, positiva: str, negativa: str):
    """Salida sigmoide de una sola neurona: > 0.5 es la clase positiva."""
    preds = modelo.predecir(image_bytes)
    if preds is None:
        return None, None
    score = float(preds[0][0])
    return (positiva if score > 0.5 else negativa), {positiva: score, negativa: 1 - score}


# --- Lunares (HAM10000, 7 clases) ---
# El orden debe coincidir con el de las salidas del modelo entrenado.
LUNARES_CLASS_NAMES = ['akiec', 'bcc', 'bkl', 'df', 'mel', 'nv', 'vasc']
LUNARES_CLASS_LABELS = {
    'akiec': 'Queratosis Actínica',
    'bcc': 'Carcinoma Basocelular',
    'bkl': 'Queratosis Benigna',
    'df': 'Dermatofibroma',
    'mel': 'Melanoma',
    'nv': 'Lunar Común (Nevus)',
    'vasc': 'Lesión Vascular',
}
_LUNARES_ETIQUETAS = [LUNARES_CLASS_LABELS[c] for c in LUNARES_CLASS_NAMES]
_lunares = _ModeloKeras("lunares.keras", LUNARES_MODEL_PATH)


def predict_lunares_class(image_bytes: bytes):
    return _clasificar_multiclase(_lunares, image_bytes, _LUNARES_ETIQUETAS)


# --- Acné (binario) ---
ACNE_CLASS_LABELS = {'acne': 'Con acné', 'no_acne': 'Sin acné'}
_acne = _ModeloKeras("acne.keras", ACNE_MODEL_PATH)


def predict_acne_class(image_bytes: bytes):
    return _clasificar_binario(
        _acne, image_bytes, ACNE_CLASS_LABELS['acne'], ACNE_CLASS_LABELS['no_acne']
    )


# --- Rosácea (binario) ---
ROSACEA_CLASS_LABELS = {'rosacea': 'Con rosácea', 'no_rosacea': 'Sin rosácea'}
_rosacea = _ModeloKeras("rosacea.keras", ROSACEA_MODEL_PATH)


def predict_rosacea_class(image_bytes: bytes):
    return _clasificar_binario(
        _rosacea, image_bytes, ROSACEA_CLASS_LABELS['rosacea'], ROSACEA_CLASS_LABELS['no_rosacea']
    )


def precargar_modelos() -> dict:
    """Carga los tres modelos por adelantado (llamar en el startup de la app).

    Sin esto, el primer usuario paga la carga completa dentro de su request.
    Devuelve el estado de cada modelo para poder reportarlo en `/health`.
    """
    return {
        "lunares": _lunares.cargar(),
        "acne": _acne.cargar(),
        "rosacea": _rosacea.cargar(),
    }
