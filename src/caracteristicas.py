"""
caracteristicas.py - Extracción de características explícitas de cada pieza.

Geometría (invariante a posición y rotación):
  - area_mm2, perimetro_mm, circularidad = 4·pi·A / P^2, solidez = A / A_envolvente_convexa
  - Rectángulo mínimo (minAreaRect): largo_mm, ancho_mm, angulo, aspecto = largo/ancho
  - studs_largo / studs_ancho = (lado_mm - correccion_borde + holgura) / 8 mm -> rejilla N x M
    Esta es la característica clave del tipo: LEGO está fabricado en un paso de
    8 mm, así que el tamaño en studs es un entero salvo error de medida.
Color (sobre la pieza erosionada y sin brillos especulares):
  - mediana de H, S, V (HSV) y de L, a, b (Lab)
Regiones internas (experimental):
  - num_studs: discos brillantes dentro de la pieza (top-hat sobre L).
Validez de la medida:
  - toca_borde: la silueta llega al borde de la zona útil -> pieza cortada.

El color y los studs se calculan sobre un recorte alrededor de cada pieza, no
sobre la imagen entera (medido con 10 piezas: de ~300 ms a ~120 ms por fotograma).
"""

import math

import cv2
import numpy as np


def _mediana_color(img_pre, mascara_pieza):
    hsv = cv2.cvtColor(img_pre, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_pre, cv2.COLOR_BGR2LAB)
    sel = mascara_pieza > 0
    # Quitar brillos especulares: muy claros y poco saturados -> no son el color del plástico
    sel_sin_brillo = sel & ~((hsv[..., 2] > 240) & (hsv[..., 1] < 60))
    if sel_sin_brillo.sum() > 0.3 * sel.sum():
        sel = sel_sin_brillo
    h = hsv[..., 0][sel].astype(np.float32)
    # El tono es circular (0 y 180 son el mismo rojo): media circular, no mediana lineal
    ang = h * (2 * math.pi / 180.0)
    h_med = (math.degrees(math.atan2(np.sin(ang).mean(), np.cos(ang).mean())) / 2.0) % 180.0
    return {
        "H": round(h_med, 1),
        "S": float(np.median(hsv[..., 1][sel])),
        "V": float(np.median(hsv[..., 2][sel])),
        "L": float(np.median(lab[..., 0][sel])),
        "a": float(np.median(lab[..., 1][sel])) - 128.0,
        "b": float(np.median(lab[..., 2][sel])) - 128.0,
        "pct_brillo": round(100.0 * (1 - sel_sin_brillo.sum() / max(1, (mascara_pieza > 0).sum())), 1),
    }


def _diametro_tophat(px_mm):
    return max(3, int(round(4.8 * px_mm * 1.6)) | 1)


def _contar_studs(img_pre, mascara_pieza, px_mm):
    """Studs = pequeños discos más claros que su entorno (reflejan la luz de arriba)."""
    if not px_mm:
        return -1
    l = cv2.cvtColor(img_pre, cv2.COLOR_BGR2LAB)[..., 0]
    d = _diametro_tophat(px_mm)
    tophat = cv2.morphologyEx(l, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d)))
    dentro = cv2.erode(mascara_pieza, np.ones((3, 3), np.uint8), iterations=2)
    vals = tophat[dentro > 0]
    if vals.size == 0 or vals.max() < 8:
        return 0
    umbral, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bin_ = ((tophat > umbral) & (dentro > 0)).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(bin_)
    area_stud = math.pi * (2.4 * px_mm) ** 2
    return int(sum(1 for i in range(1, n) if 0.15 * area_stud <= stats[i, cv2.CC_STAT_AREA] <= 2.0 * area_stud))


def extraer(contorno, img_pre, cfg):
    px_mm = cfg["escala"]["px_por_mm"]
    k = px_mm or 1.0  # sin calibrar, las medidas quedan en píxeles
    paso, holgura = cfg["lego"]["paso_stud_mm"], cfg["lego"]["holgura_mm"]
    corr = cfg["lego"].get("correccion_borde_mm", 0.0) if px_mm else 0.0

    area = cv2.contourArea(contorno)
    perim = cv2.arcLength(contorno, True)
    hull = cv2.convexHull(contorno)
    (cx, cy), (w, h), ang = cv2.minAreaRect(contorno)
    # Medida corregida del sesgo sistemático de la segmentación
    largo, ancho = max(w, h) / k - corr, min(w, h) / k - corr
    M = cv2.moments(contorno)

    # Recorte alrededor de la pieza, con margen para que el top-hat no note el corte
    alto_img, ancho_img = img_pre.shape[:2]
    bx, by, bw, bh = cv2.boundingRect(contorno)
    margen = _diametro_tophat(px_mm) if px_mm else 10
    x0, y0 = max(0, bx - margen), max(0, by - margen)
    recorte = img_pre[y0:min(alto_img, by + bh + margen), x0:min(ancho_img, bx + bw + margen)]
    mascara = np.zeros(recorte.shape[:2], np.uint8)
    cv2.drawContours(mascara, [contorno], -1, 255, cv2.FILLED, offset=(-x0, -y0))
    mascara_int = cv2.erode(mascara, np.ones((5, 5), np.uint8), iterations=2)
    if mascara_int.sum() == 0:
        mascara_int = mascara

    f = {
        "cx": round(M["m10"] / M["m00"], 1) if M["m00"] else cx,
        "cy": round(M["m01"] / M["m00"], 1) if M["m00"] else cy,
        "area_mm2": round(area / (k * k), 1),
        "perimetro_mm": round(perim / k, 1),
        "circularidad": round(4 * math.pi * area / (perim * perim), 3) if perim else 0,
        "solidez": round(area / cv2.contourArea(hull), 3) if cv2.contourArea(hull) else 0,
        "largo_mm": round(largo, 2),
        "ancho_mm": round(ancho, 2),
        "aspecto": round(largo / ancho, 3) if ancho else 0,
        "angulo": round(ang, 1),
        "studs_largo": round((largo + holgura) / paso, 2),
        "studs_ancho": round((ancho + holgura) / paso, 2),
        "num_studs": _contar_studs(recorte, mascara_int, px_mm),
        "toca_borde": bx <= 1 or by <= 1 or bx + bw >= ancho_img - 1 or by + bh >= alto_img - 1,
        "unidades": "mm" if px_mm else "px",
    }
    f.update(_mediana_color(recorte, mascara_int))
    return f
