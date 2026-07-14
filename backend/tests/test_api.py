"""Tests de la API de PielSana IA.

Los modelos Keras se mockean (monkeypatch), así que no hacen falta los `.keras`
reales ni ejecutar TensorFlow para correr estos tests.

Ejecutar desde la raíz del repo:  python -m pytest backend/tests
Requiere: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app

client = TestClient(app)


def _png_bytes(size=(16, 16), color=(120, 80, 60)) -> bytes:
    """Genera los bytes de un PNG válido en memoria."""
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


# --- Info de condiciones (no usa modelos) ---

def test_condition_existente():
    resp = client.get("/skin/api/condition/acne")
    assert resp.status_code == 200
    assert resp.json()["name"] == "acne"


def test_condition_inexistente():
    resp = client.get("/skin/api/condition/noexiste")
    assert resp.status_code == 404


# --- Validación de subida (leer_imagen_validada) ---

def test_analyze_rechaza_no_imagen():
    resp = client.post(
        "/skin/api/analyze-lunares",
        files={"file": ("nota.txt", b"esto no es una imagen", "text/plain")},
    )
    assert resp.status_code == 400


def test_analyze_rechaza_imagen_corrupta():
    resp = client.post(
        "/skin/api/analyze-lunares",
        files={"file": ("falsa.png", b"\x89PNG basura no decodificable", "image/png")},
    )
    assert resp.status_code == 400


def test_analyze_rechaza_imagen_gigante():
    grande = b"\x00" * (8 * 1024 * 1024 + 1)  # supera MAX_IMAGE_BYTES (8 MB)
    resp = client.post(
        "/skin/api/analyze-lunares",
        files={"file": ("grande.png", grande, "image/png")},
    )
    assert resp.status_code == 413


# --- Predicción con el modelo mockeado ---

def test_analyze_lunares_ok(monkeypatch):
    monkeypatch.setattr(
        "backend.controllers.skin.predict_lunares_class",
        lambda image_bytes: ("Melanoma", {"Melanoma": 0.9}),
    )
    resp = client.post(
        "/skin/api/analyze-lunares",
        files={"file": ("lunar.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["prediccion"] == "Melanoma"
    assert data["probabilidades"] == {"Melanoma": 0.9}


def test_analyze_acne_ok(monkeypatch):
    monkeypatch.setattr(
        "backend.controllers.skin.predict_acne_class",
        lambda image_bytes: ("Con acné", {"Con acné": 0.8, "Sin acné": 0.2}),
    )
    resp = client.post(
        "/skin/api/analyze-acne",
        files={"file": ("cara.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["prediccion"] == "Con acné"


def test_analyze_modelo_no_disponible(monkeypatch):
    # Si el modelo no carga, predict_* devuelve (None, None) -> 500.
    monkeypatch.setattr(
        "backend.controllers.skin.predict_lunares_class",
        lambda image_bytes: (None, None),
    )
    resp = client.post(
        "/skin/api/analyze-lunares",
        files={"file": ("lunar.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 500


# --- OpenAI: error de configuración (sin API key) ---

def test_openai_recomendaciones_sin_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post(
        "/skin/openai-recomendaciones",
        json={"prediccion": "acné"},
    )
    assert resp.status_code == 503
