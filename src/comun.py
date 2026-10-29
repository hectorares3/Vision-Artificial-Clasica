"""
comun.py - Utilidades compartidas: rutas del proyecto, lectura/escritura de la
configuración y apertura de la cámara con los ajustes automáticos desactivados.
"""

import json
import os
import sys

import cv2

# Raíz del proyecto = carpeta padre de src/. Así los scripts funcionan se
# lancen desde donde se lancen.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CONFIG = os.path.join(RAIZ, "config", "config.json")
RUTA_UMBRALES = os.path.join(RAIZ, "config", "umbrales.json")


def ruta(*partes):
    """Ruta absoluta dentro del proyecto."""
    return os.path.join(RAIZ, *partes)


def cargar_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def guardar_json(path, datos):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def cargar_config():
    return cargar_json(RUTA_CONFIG)


def guardar_config(cfg):
    guardar_json(RUTA_CONFIG, cfg)


def cargar_umbrales():
    return cargar_json(RUTA_UMBRALES)


def leer_imagen(path):
    """cv2.imread falla con tildes/ñ en rutas de Windows; esto no."""
    import numpy as np
    datos = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"No se pudo leer la imagen: {path}")
    return img


def guardar_imagen(path, img):
    """Equivalente a cv2.imwrite pero seguro con tildes en la ruta."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def abrir_camara(cfg_cam):
    """Abre la webcam con DirectShow (Windows) y fija exposición, balance de
    blancos y enfoque. Sin esto el color de una pieza cambia según qué otras
    piezas haya en la escena y el árbol de decisión deja de funcionar."""
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    cap = cv2.VideoCapture(cfg_cam["indice"], backend)
    if not cap.isOpened():
        sys.exit(f"No se pudo abrir la cámara {cfg_cam['indice']}. "
                 "¿Está abierta en otra aplicación (app Cámara, Teams...)?")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg_cam["ancho"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg_cam["alto"])
    fijar_manual(cap, cfg_cam)
    return cap


def fijar_manual(cap, cfg_cam):
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 = manual en DirectShow
    cap.set(cv2.CAP_PROP_EXPOSURE, cfg_cam["exposicion"])
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    cap.set(cv2.CAP_PROP_WB_TEMPERATURE, cfg_cam["wb_temperatura"])
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_FOCUS, cfg_cam["enfoque"])
    # La ganancia también hay que fijarla: con la exposición en manual el driver
    # la subía sola hasta 255 (máximo ruido). Mejor más luz y ganancia baja.
    if cfg_cam.get("ganancia") is not None:
        cap.set(cv2.CAP_PROP_GAIN, cfg_cam["ganancia"])


def leer_fotogramas(cap, n):
    """n fotogramas seguidos. Para el modelo del fondo: varias fotos miden
    también el ruido temporal del sensor, no solo la textura del fieltro."""
    fotos = []
    while len(fotos) < n:
        ok, f = cap.read()
        if not ok:
            break
        fotos.append(f)
    return fotos


def fijar_auto(cap):
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)


def propiedades_camara(cap):
    """Lo que la cámara dice tener realmente (puede diferir de lo pedido)."""
    nombres = ["FRAME_WIDTH", "FRAME_HEIGHT", "FPS", "AUTO_EXPOSURE", "EXPOSURE",
               "GAIN", "AUTO_WB", "WB_TEMPERATURE", "AUTOFOCUS", "FOCUS",
               "BRIGHTNESS", "CONTRAST", "SATURATION", "SHARPNESS"]
    return {n.lower(): cap.get(getattr(cv2, "CAP_PROP_" + n)) for n in nombres}


def rectificar(img, cfg):
    """Vista cenital métrica: aplica la homografía de calibrar_escala.py, que
    corrige la inclinación de la cámara (misma escala en todo el tapete)."""
    h = cfg.get("homografia", {})
    if h.get("usar") and h.get("matriz"):
        import numpy as np
        return cv2.warpPerspective(img, np.array(h["matriz"], np.float64), (h["ancho"], h["alto"]))
    return img


def recortar_roi(img, cfg):
    r = cfg["roi"]
    if r.get("ancho") and r.get("alto"):
        return img[r["y"]:r["y"] + r["alto"], r["x"]:r["x"] + r["ancho"]]
    return img
