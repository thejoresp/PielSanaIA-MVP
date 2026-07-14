from PIL import Image
from io import BytesIO
import tensorflow as tf
from tensorflow.keras.preprocessing.image import img_to_array
from backend.config.model_config import LUNARES_MODEL_PATH, ACNE_MODEL_PATH, ROSACEA_MODEL_PATH


def _preprocesar_imagen(image_bytes: bytes):
    """Preprocesado uniforme: RGB -> resize 224x224 -> /255.0 -> shape (1,224,224,3)."""
    img = Image.open(BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_resized = img.resize((224, 224))
    img_array = img_to_array(img_resized) / 255.0
    return img_array.reshape((1, 224, 224, 3))


# --- INICIO: Funciones para modelo lunares.keras ---
LUNARES_MODEL = None
LUNARES_CLASS_NAMES = ['akiec', 'bcc', 'bkl', 'df', 'mel', 'nv', 'vasc']
LUNARES_CLASS_LABELS = {
    'akiec': 'Queratosis Actínica',
    'bcc': 'Carcinoma Basocelular',
    'bkl': 'Queratosis Benigna',
    'df': 'Dermatofibroma',
    'mel': 'Melanoma',
    'nv': 'Lúnar Común (Nevus)',
    'vasc': 'Lesión Vascular'
}

def load_lunares_model():
    global LUNARES_MODEL
    if LUNARES_MODEL is None:
        try:
            print(f"Cargando modelo lunares.keras desde {LUNARES_MODEL_PATH}...")
            LUNARES_MODEL = tf.keras.models.load_model(LUNARES_MODEL_PATH)
            print("Modelo lunares.keras cargado exitosamente.")
        except Exception as e:
            print(f"Error cargando el modelo lunares.keras: {e}")
            LUNARES_MODEL = None
    return LUNARES_MODEL

def predict_lunares_class(image_bytes: bytes):
    model = load_lunares_model()
    if model is None:
        print("El modelo lunares.keras no está cargado.")
        return None, None
    try:
        img_array = _preprocesar_imagen(image_bytes)
        preds = model.predict(img_array)
        pred_idx = preds.argmax(axis=1)[0]
        pred_class = LUNARES_CLASS_NAMES[pred_idx]
        pred_label = LUNARES_CLASS_LABELS[pred_class]
        probabilities = {LUNARES_CLASS_LABELS[LUNARES_CLASS_NAMES[i]]: float(preds[0][i]) for i in range(len(LUNARES_CLASS_NAMES))}
        return pred_label, probabilities
    except Exception as e:
        print(f"Error al predecir con lunares.keras: {e}")
        return None, None
# --- FIN: Funciones para modelo lunares.keras --- 

# --- INICIO: Funciones para modelo acne.keras ---
ACNE_CLASS_NAMES = ['acne', 'no_acne']
ACNE_CLASS_LABELS = {
    'acne': 'Con acné',
    'no_acne': 'Sin acné'
}
ACNE_MODEL = None

def load_acne_model():
    global ACNE_MODEL
    if ACNE_MODEL is None:
        try:
            print(f"Cargando modelo acne.keras desde {ACNE_MODEL_PATH}...")
            ACNE_MODEL = tf.keras.models.load_model(ACNE_MODEL_PATH)
            print("Modelo acne.keras cargado exitosamente.")
        except Exception as e:
            print(f"Error cargando el modelo acne.keras: {e}")
            ACNE_MODEL = None
    return ACNE_MODEL

def predict_acne_class(image_bytes: bytes):
    model = load_acne_model()
    if model is None:
        print("El modelo acne.keras no está cargado.")
        return None, None
    try:
        img_array = _preprocesar_imagen(image_bytes)
        preds = model.predict(img_array)
        # Como es binario, salida sigmoid: 0 = no_acne, 1 = acne
        pred_idx = int(preds[0][0] > 0.5)
        pred_class = ACNE_CLASS_NAMES[pred_idx]
        pred_label = ACNE_CLASS_LABELS[pred_class]
        probabilities = {
            ACNE_CLASS_LABELS[ACNE_CLASS_NAMES[1]]: float(preds[0][0]),
            ACNE_CLASS_LABELS[ACNE_CLASS_NAMES[0]]: float(1 - preds[0][0])
        }
        return pred_label, probabilities
    except Exception as e:
        print(f"Error al predecir con acne.keras: {e}")
        return None, None
# --- FIN: Funciones para modelo acne.keras ---

# --- INICIO: Funciones para modelo rosacea.keras ---
ROSACEA_CLASS_NAMES = ['rosacea', 'no_rosacea']
ROSACEA_CLASS_LABELS = {
    'rosacea': 'Con rosácea',
    'no_rosacea': 'Sin rosácea'
}
ROSACEA_MODEL = None

def load_rosacea_model():
    global ROSACEA_MODEL
    if ROSACEA_MODEL is None:
        try:
            print(f"Cargando modelo rosacea.keras desde {ROSACEA_MODEL_PATH}...")
            ROSACEA_MODEL = tf.keras.models.load_model(ROSACEA_MODEL_PATH)
            print("Modelo rosacea.keras cargado exitosamente.")
        except Exception as e:
            print(f"Error cargando el modelo rosacea.keras: {e}")
            ROSACEA_MODEL = None
    return ROSACEA_MODEL

def predict_rosacea_class(image_bytes: bytes):
    model = load_rosacea_model()
    if model is None:
        print("El modelo rosacea.keras no está cargado.")
        return None, None
    try:
        img_array = _preprocesar_imagen(image_bytes)
        preds = model.predict(img_array)
        pred_idx = int(preds[0][0] > 0.5)
        pred_class = ROSACEA_CLASS_NAMES[pred_idx]
        pred_label = ROSACEA_CLASS_LABELS[pred_class]
        probabilities = {
            ROSACEA_CLASS_LABELS[ROSACEA_CLASS_NAMES[1]]: float(preds[0][0]),
            ROSACEA_CLASS_LABELS[ROSACEA_CLASS_NAMES[0]]: float(1 - preds[0][0])
        }
        return pred_label, probabilities
    except Exception as e:
        print(f"Error al predecir con rosacea.keras: {e}")
        return None, None
# --- FIN: Funciones para modelo rosacea.keras --- 