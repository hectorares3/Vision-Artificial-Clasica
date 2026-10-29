"""
segmentacion.py - Nivel 1 (detección): separa las piezas del fieltro verde.

Método (sustracción de fondo en Lab):
  1. Modelo del fondo a partir de varias fotos del tapete vacío
     (datos/calibracion/fondo/):
       - color esperado en cada píxel: media de las fotos muy suavizada. Sigue
         el gradiente de iluminación pero no la textura del fieltro;
       - ruido esperado en cada píxel (sigma local). El ruido crece con el
         brillo (medido: residuo mediano 1,97 en zonas oscuras y 2,89 en el
         foco de luz), así que una sigma global da falsos positivos en el foco.
  2. En cada imagen nueva se mide la distancia en Lab al modelo.
  3. Compensación de deriva: la luz cambia algo entre la foto del fondo y la
     escena (medido: +3,5 unidades de L a los 4 minutos). Ese cambio es lento
     en el espacio, así que se estima sobre los píxeles que ya parecen fondo
     y se resta antes de umbralizar.
  4. Pieza = distancia > k_sigma sigmas locales. El umbral se justifica con
     resultados/figuras/hist_fondo.png.
  5. Apertura/cierre morfológicos y filtro de área mínima.

Se usa Lab porque separa luminosidad (L) de color (a, b): el fieltro verde y
una pieza roja difieren mucho en a, aunque tengan la misma L.
"""

import glob
import os
import sys

import cv2
import numpy as np

import comun

PESO_L = 0.5            # la L pesa la mitad: reduce que las sombras suaves se detecten como pieza
SIGMA_MODELO_PX = 25    # suavizado del color y del ruido esperados del fondo
SIGMA_DERIVA_PX = 40    # escala espacial de la deriva de iluminación que se compensa


def preprocesar(img, cfg):
    """Rectificación (homografía) + ROI + suavizado ligero contra el ruido del
    sensor + normalización con el parche blanco si está configurado. Las
    coordenadas del parche son relativas a la ROI."""
    img = comun.rectificar(img, cfg)
    img = comun.recortar_roi(img, cfg)
    img = cv2.GaussianBlur(img, (5, 5), 0)
    ref = cfg["referencia_blanca"]
    if ref.get("usar") and ref.get("ancho"):
        parche = img[ref["y"]:ref["y"] + ref["alto"], ref["x"]:ref["x"] + ref["ancho"]]
        medio = parche.reshape(-1, 3).mean(axis=0)
        img = np.clip(img.astype(np.float32) * (230.0 / np.maximum(medio, 1)), 0, 255).astype(np.uint8)
    return img


def a_lab(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[..., 0] *= PESO_L
    return lab


def _media_ponderada(x, peso, sigma_px, f=4):
    """Media local de x usando solo los píxeles con peso 1 (convolución
    normalizada). Los huecos de las piezas se rellenan con el fondo de
    alrededor. Se calcula a 1/f de resolución porque es muy suave."""
    alto, ancho = peso.shape
    peq = (ancho // f, alto // f)
    xs = cv2.GaussianBlur(cv2.resize(x * peso[..., None], peq, interpolation=cv2.INTER_AREA), (0, 0), sigma_px / f)
    ps = cv2.GaussianBlur(cv2.resize(peso, peq, interpolation=cv2.INTER_AREA), (0, 0), sigma_px / f)
    return cv2.resize(xs / np.maximum(ps, 1e-3)[..., None], (ancho, alto), interpolation=cv2.INTER_LINEAR)


class ModeloFondo:
    def __init__(self, fondos_bgr, k_sigma, compensar=True):
        """fondos_bgr: fotos preprocesadas del tapete vacío (una o varias)."""
        self.k_sigma, self.compensar = k_sigma, compensar
        suma = sum(a_lab(f) for f in fondos_bgr)
        self.media = cv2.GaussianBlur(suma / len(fondos_bgr), (0, 0), sigmaX=SIGMA_MODELO_PX)

        suma_resid, muestras = np.zeros(self.media.shape[:2], np.float32), []
        for f in fondos_bgr:
            r = np.linalg.norm(a_lab(f) - self.media, axis=2)
            suma_resid += r
            muestras.append(r[::4, ::4].ravel())
        muestras = np.concatenate(muestras)
        # Sigma global robusta (MAD): fija la escala de "una sigma"
        self.sigma_global = float(1.4826 * np.median(np.abs(muestras - np.median(muestras)))) + 1e-6
        # Sigma local: residuo medio del entorno, llevado a la escala de la global.
        # El suelo evita sigmas diminutas en zonas muy oscuras y uniformes.
        local = cv2.GaussianBlur(suma_resid / len(fondos_bgr), (0, 0), sigmaX=SIGMA_MODELO_PX)
        self.sigma = np.maximum(local * (self.sigma_global / muestras.mean()), 0.5 * self.sigma_global)
        # Distancias del propio fondo (submuestreadas), para el histograma de justificación
        self.dist_fondo = muestras / np.tile(self.sigma[::4, ::4].ravel(), len(fondos_bgr))

    @classmethod
    def desde_imagen(cls, img_bgr, **opciones):
        """Sin fotos de fondo: estima el fieltro con un filtro de mediana enorme
        (las piezas son pequeñas frente al tapete). Peor que tener el fondo."""
        peq = cv2.resize(img_bgr, None, fx=0.25, fy=0.25)
        fondo = cv2.medianBlur(peq, 51)
        fondo = cv2.resize(fondo, (img_bgr.shape[1], img_bgr.shape[0]))
        return cls([fondo], **opciones)

    def distancia(self, img_bgr):
        if img_bgr.shape[:2] != self.media.shape[:2]:
            raise ValueError("La imagen y el fondo tienen distinto tamaño: ¿cambiaste resolución, ROI u homografía?")
        d = a_lab(img_bgr) - self.media
        if self.compensar:
            parece_fondo = (np.linalg.norm(d, axis=2) / self.sigma < self.k_sigma).astype(np.float32)
            d -= _media_ponderada(d, parece_fondo, SIGMA_DERIVA_PX)
        return np.linalg.norm(d, axis=2) / self.sigma


def _opciones(cfg):
    s = cfg["segmentacion"]
    return {"k_sigma": s["k_sigma"], "compensar": s.get("compensar_iluminacion", True)}


def rutas_fondo(cfg):
    """Fotos del tapete vacío: la carpeta de fondo o, si no existe, fondo.png."""
    s = cfg["segmentacion"]
    rutas = sorted(glob.glob(os.path.join(comun.ruta(s["fondo_carpeta"]), "*.png")))
    if not rutas and os.path.exists(comun.ruta(s["fondo_imagen"])):
        rutas = [comun.ruta(s["fondo_imagen"])]
    return rutas


def cargar_modelo_fondo(cfg, img_si_no_hay=None):
    rutas = rutas_fondo(cfg)
    if rutas:
        return ModeloFondo([preprocesar(comun.leer_imagen(r), cfg) for r in rutas], **_opciones(cfg))
    if img_si_no_hay is None:
        sys.exit("No hay fotos del tapete vacío. Captúralas con 1_capturar_calibracion.bat (tecla f) "
                 "o con la tecla b en 5_detectar_en_vivo.bat.")
    print("AVISO: no hay fotos del tapete vacío; se estima el fondo de la propia imagen.")
    return ModeloFondo.desde_imagen(img_si_no_hay, **_opciones(cfg))


def guardar_fondo(fotogramas, cfg):
    """Sustituye las fotos del tapete vacío (sin preprocesar). fondo.png es la
    primera, para las figuras de la memoria."""
    s = cfg["segmentacion"]
    carpeta = comun.ruta(s["fondo_carpeta"])
    os.makedirs(carpeta, exist_ok=True)
    for vieja in glob.glob(os.path.join(carpeta, "fondo_*.png")):
        os.remove(vieja)  # no mezclar fotos de dos iluminaciones distintas
    for i, f in enumerate(fotogramas):
        comun.guardar_imagen(os.path.join(carpeta, f"fondo_{i:02d}.png"), f)
    comun.guardar_imagen(comun.ruta(s["fondo_imagen"]), fotogramas[0])


def segmentar(img_pre, modelo, cfg):
    """Devuelve (máscara binaria, lista de contornos de piezas)."""
    s = cfg["segmentacion"]
    dist = modelo.distancia(img_pre)
    mascara = (dist > s["k_sigma"]).astype(np.uint8) * 255

    ka = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (s["apertura_px"],) * 2)
    kc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (s["cierre_px"],) * 2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, ka)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kc)

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    px_mm = cfg["escala"]["px_por_mm"] or 1.0
    area_min_px = s["area_min_mm2"] * px_mm * px_mm if cfg["escala"]["px_por_mm"] else 200
    contornos = [c for c in contornos if cv2.contourArea(c) >= area_min_px]

    # Rellenar huecos interiores para que la máscara final sea la silueta completa
    final = np.zeros_like(mascara)
    cv2.drawContours(final, contornos, -1, 255, cv2.FILLED)
    return final, contornos
