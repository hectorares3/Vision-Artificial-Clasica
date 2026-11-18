"""
Reto 07 - Visión artificial clásica: inventario de piezas LEGO.

Pipeline: imagen RGB -> HSV/Lab -> segmentación (todo lo que no es tapete verde)
-> piezas (contornos) -> características (ancho/largo en mm, color Lab)
-> árbol de decisión -> clase = tipo + color -> inventario.

Uso:  python lego.py [foto.jpg|foto.heic]   (sin argumento abre un diálogo)
"""
import os
import sys
from collections import Counter
import cv2
import numpy as np

# ------------------------- PARÁMETROS (medidos en las fotos de prueba) -------------------
PX_MM = 8.0                             # escala con el móvil a altura fija (2x2 = 16 mm ~ 128 px)
VERDE_BAJO = np.array([35, 40, 25])     # rango HSV del fieltro verde
VERDE_ALTO = np.array([85, 255, 255])
AREA_MIN_MM2 = 40                       # descarta ruido más pequeño que esto
RECT_MIN = 0.65                         # área contorno / área rectángulo (piezas >= 0.70 incluso con reflejo)
ANCHO_MIN_MM = 5                        # pieza más estrecha 6.9 mm; tiras de cartón del borde 2-4 mm

# Nodo de tamaño: (límite superior en mm, nº de tetones). Cada umbral está a mitad de camino
# entre los grupos medidos en las fotos: 1 tetón 6.9-12.3 | 2: 15.0-17.7 | 4: 29.5-32.4
# | 6: 46.0-50.1 | 8: 60.4-63.2 mm
LIMITES_MM = [(13.5, 1), (23.5, 2), (39.0, 4), (55.0, 6), (70.0, 8)]


# ------------------------------- ÁRBOL DE DECISIÓN ------------------------------------
def tetones(mm):
    """Convierte una medida en mm al nº de tetones según LIMITES_MM (None si es demasiado grande)."""
    for limite, n in LIMITES_MM:
        if mm < limite:
            return n
    return None


def clasificar_tipo(ancho_mm, largo_mm):
    w, l = tetones(ancho_mm), tetones(largo_mm)
    if w is None or l is None:
        return "desconocido"
    return f"{w}x{l}"


def clasificar_color(a, b, v):
    """Nodo de color con Lab de OpenCV (a, b centrados en 128) y brillo V de HSV.
    Umbrales a mitad de camino entre los rangos medidos en las fotos (ver tabla del trabajo)."""
    if b < 110:   return "azul"       # azul b 72-105 (incl. transparente) | resto >= 122
    if a > 160:   return "rojo"       # rojo a 172-187 | marrón <= 153
    if a > 132:                       # rojizos: marrón a 133-153 | beige/blanco/gris <= 131
        return "rosa" if v > 220 else "marron"   # rosa V 249 | marrón V <= 200
    if b > 178:   return "amarillo"   # amarillo b 196-198 | beige <= 160
    if b > 145:   return "beige"      # beige b 156-160 | blanco <= 135
    if v < 190:   return "negro"      # negro V 13-173 (bajo la lámpara) | blanco/gris >= 208
    if b >= 130 or v > 245:
        return "blanco"               # blanco b 132-135 (o sobreexpuesto V>245) | gris b <= 128
    return "gris"


# --------------------------------- PROGRAMA PRINCIPAL ---------------------------------
def leer_imagen(ruta):
    if ruta.lower().endswith(".heic"):            # fotos de iPhone
        from PIL import Image
        import pillow_heif
        pillow_heif.register_heif_opener()
        return cv2.cvtColor(np.array(Image.open(ruta).convert("RGB")), cv2.COLOR_RGB2BGR)
    return cv2.imdecode(np.fromfile(ruta, np.uint8), cv2.IMREAD_COLOR)   # admite tildes


def analizar(ruta, devolver_inventario=False):
    img = leer_imagen(ruta)
    if img is None:
        sys.exit(f"No se pudo leer {ruta}")
    suave = cv2.GaussianBlur(img, (5, 5), 0)
    hsv = cv2.cvtColor(suave, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(suave, cv2.COLOR_BGR2LAB)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    alto, ancho_img = img.shape[:2]

    # 1) Segmentación: zona del tapete (envolvente del verde) menos lo verde = piezas
    verde = cv2.inRange(hsv, VERDE_BAJO, VERDE_ALTO)
    cs, _ = cv2.findContours(verde, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    zona = np.zeros_like(verde)
    cv2.drawContours(zona, [cv2.convexHull(max(cs, key=cv2.contourArea))], -1, 255, -1)
    piezas = cv2.bitwise_and(cv2.erode(zona, k, iterations=3), cv2.bitwise_not(verde))
    piezas = cv2.morphologyEx(piezas, cv2.MORPH_OPEN, k)
    piezas = cv2.morphologyEx(piezas, cv2.MORPH_CLOSE, k, iterations=2)
    cs, _ = cv2.findContours(piezas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 2) Detección + características + clasificación de cada pieza
    inventario = Counter()
    print(f"{'#':>2} {'ancho':>6} {'largo':>6} {'rect':>5} {'a':>4} {'b':>4} {'V':>4}  clase")
    n = 0
    for c in cs:
        x, y, w0, h0 = cv2.boundingRect(c)
        if x <= 2 or y <= 2 or x + w0 >= ancho_img - 2 or y + h0 >= alto - 2:
            continue                                   # corta el borde de la foto: incompleta
        (cx, cy), (w, h), ang = cv2.minAreaRect(c)     # rectángulo orientado -> invariante a giro
        area = cv2.contourArea(c)
        rect = area / (w * h + 1e-6)
        if area / PX_MM**2 < AREA_MIN_MM2 or rect < RECT_MIN:
            continue                                   # ruido / sombras / no rectangular
        ancho, largo = sorted((w / PX_MM, h / PX_MM))
        if ancho < ANCHO_MIN_MM:
            continue                                   # tiras finas (borde del tapete / cartón)

        mask = np.zeros(piezas.shape, np.uint8)
        cv2.drawContours(mask, [c], -1, 255, -1)
        mask = cv2.erode(mask, k) > 0                  # quita el borde (mezcla con el verde)
        brillo = (hsv[..., 2] >= 250) & (hsv[..., 1] < 40)   # reflejo especular de la lámpara
        if (mask & ~brillo).sum() > 0.3 * mask.sum():  # si queda suficiente pieza sin reflejo,
            mask &= ~brillo                            # el color se mide sin el reflejo
        a, b = int(np.median(lab[..., 1][mask])), int(np.median(lab[..., 2][mask]))
        v = int(np.median(hsv[..., 2][mask]))

        clase = f"{clasificar_tipo(ancho, largo)} {clasificar_color(a, b, v)}"
        inventario[clase] += 1
        n += 1
        print(f"{n:>2} {ancho:6.1f} {largo:6.1f} {rect:5.2f} {a:4d} {b:4d} {v:4d}  {clase}")

        caja = cv2.boxPoints(((cx, cy), (w, h), ang)).astype(int)
        cv2.drawContours(img, [caja], -1, (255, 0, 255), 6)
        cv2.putText(img, f"{n}:{clase}", (int(cx) - 120, int(cy)), cv2.FONT_HERSHEY_SIMPLEX,
                    2, (0, 0, 0), 12)
        cv2.putText(img, f"{n}:{clase}", (int(cx) - 120, int(cy)), cv2.FONT_HERSHEY_SIMPLEX,
                    2, (255, 255, 255), 4)

    # 3) Interpretación: inventario por tipo y color
    print(f"\nINVENTARIO ({n} piezas)")
    for clase, cnt in sorted(inventario.items()):
        print(f"  {clase:<14} x{cnt}")

    salida = os.path.splitext(ruta)[0] + "_resultado.jpg"
    cv2.imencode(".jpg", img)[1].tofile(salida)
    print(f"\nImagen guardada en {salida}")
    return inventario if devolver_inventario else img


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        from tkinter import Tk, filedialog
        Tk().withdraw()
        ruta = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.heic *.HEIC")])
        if not ruta:
            sys.exit("No se eligió imagen")
    res = analizar(ruta)
    escala = min(1.0, 900 / max(res.shape[:2]))
    cv2.imshow("LEGO", cv2.resize(res, None, fx=escala, fy=escala))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    input("\nPulsa Enter para salir...")      # mantiene la consola abierta en el .exe
