"""
calibrar_escala.py - Rectificación de perspectiva (homografía), escala (px/mm)
y zona útil (ROI) a partir de datos/calibracion/regla.png. Es la justificación
experimental de la resolución espacial que pide la convocatoria.

regla.png: el tapete con una hoja de tamaño conocido (A4 = 297 x 210 mm),
plana y con las cuatro esquinas intactas.

Por qué una homografía y no una sola distancia: si la cámara no está del todo
perpendicular, la escala cambia de un lado a otro de la imagen (medido en
este montaje: el borde superior del A4 a 3,15 px/mm y el inferior a ~3,99).
Con las 4 esquinas de un rectángulo conocido se calcula la transformación que
lleva la imagen a una vista cenital con la misma escala en todo el tapete.
No corrige la pared lateral de las piezas altas: eso solo lo reduce subir la cámara.

Uso:  python src/calibrar_escala.py
1) Haz clic en las 4 esquinas de la hoja (en cualquier orden) y pulsa una tecla.
2) Escribe sus medidas en mm (Enter = A4, 297 x 210).
3) En la imagen ya rectificada, arrastra la zona útil (solo tapete) y pulsa
   ENTER. Se recorta sola para no incluir las cuñas negras que deja la
   rectificación en los bordes (ESC = toda la zona sin cuñas).
"""

import math

import cv2
import numpy as np

import comun

puntos = []


def clic(evento, x, y, flags, img):
    if evento == cv2.EVENT_LBUTTONDOWN and len(puntos) < 4:
        puntos.append((x, y))
        cv2.circle(img, (x, y), 6, (0, 0, 255), -1)
        cv2.putText(img, str(len(puntos)), (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.imshow("regla", img)


def ordenar_esquinas(p):
    """Orden sup-izq, sup-der, inf-der, inf-izq, sea cual sea el orden de los clics."""
    p = np.array(p, np.float32)
    suma, resta = p.sum(axis=1), p[:, 1] - p[:, 0]
    return np.array([p[suma.argmin()], p[resta.argmin()], p[suma.argmax()], p[resta.argmax()]], np.float32)


def pedir_medidas():
    txt = input("Medidas de la hoja en mm, p. ej. 297x210 (Enter = A4): ").strip().lower()
    if not txt:
        return 297.0, 210.0
    a, b = (float(x.replace(",", ".")) for x in txt.replace("*", "x").split("x"))
    return max(a, b), min(a, b)


def main():
    cfg = comun.cargar_config()
    img = comun.leer_imagen(comun.ruta("datos", "calibracion", "regla.png"))
    vista = img.copy()

    cv2.namedWindow("regla", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("regla", 1280, 720)
    cv2.setMouseCallback("regla", clic, vista)
    cv2.imshow("regla", vista)
    print("Haz clic en las 4 esquinas de la hoja y pulsa cualquier tecla.")
    while len(puntos) < 4:
        if cv2.waitKey(50) == 27:
            return
    cv2.waitKey(0)

    sup_izq, sup_der, inf_der, inf_izq = esq = ordenar_esquinas(puntos)
    lado_largo, lado_corto = pedir_medidas()
    # El lado real más largo va con el par de lados más largo en la imagen
    horiz_px = (np.linalg.norm(sup_der - sup_izq) + np.linalg.norm(inf_der - inf_izq)) / 2
    vert_px = (np.linalg.norm(inf_izq - sup_izq) + np.linalg.norm(inf_der - sup_der)) / 2
    ancho_mm, alto_mm = (lado_largo, lado_corto) if horiz_px >= vert_px else (lado_corto, lado_largo)

    # Escala de cada lado ANTES de corregir: es la prueba de la inclinación para la memoria
    print("\nEscala de cada lado de la hoja en la imagen original:")
    lados = [("superior", sup_izq, sup_der, ancho_mm), ("inferior", inf_izq, inf_der, ancho_mm),
             ("izquierdo", sup_izq, inf_izq, alto_mm), ("derecho", sup_der, inf_der, alto_mm)]
    for nombre, a, b, mm in lados:
        px_mm_lado = np.linalg.norm(b - a) / mm
        print(f"  {nombre:<10} {px_mm_lado:.3f} px/mm")
        pa, pb, pm = (tuple(int(v) for v in q) for q in (a, b, (a + b) / 2 + 8))
        cv2.line(vista, pa, pb, (0, 0, 255), 2)
        cv2.putText(vista, f"{px_mm_lado:.2f} px/mm", pm, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)

    # Homografía imagen -> plano del tapete en mm, y luego a píxeles con una
    # escala única: la media de la hoja, para no perder ni inventar resolución.
    h_mm = cv2.getPerspectiveTransform(esq, np.float32([[0, 0], [ancho_mm, 0], [ancho_mm, alto_mm], [0, alto_mm]]))
    px_mm = math.sqrt(cv2.contourArea(esq) / (ancho_mm * alto_mm))
    alto_img, ancho_img = img.shape[:2]
    bordes = cv2.perspectiveTransform(
        np.float32([[[0, 0]], [[ancho_img, 0]], [[ancho_img, alto_img]], [[0, alto_img]]]), h_mm).reshape(-1, 2)
    x_min, y_min = bordes.min(axis=0)
    x_max, y_max = bordes.max(axis=0)
    ancho_out, alto_out = int(math.ceil((x_max - x_min) * px_mm)), int(math.ceil((y_max - y_min) * px_mm))
    if ancho_out * alto_out > 4 * ancho_img * alto_img:
        print("ERROR: la imagen rectificada saldría enorme: revisa los clics en las esquinas.")
        return
    escala = np.array([[px_mm, 0, -x_min * px_mm], [0, px_mm, -y_min * px_mm], [0, 0, 1]])
    cfg["homografia"].update({"usar": True, "matriz": (escala @ h_mm).tolist(),
                              "ancho": ancho_out, "alto": alto_out})
    # Rectángulo con imagen real (sin las cuñas negras de la rectificación). En
    # el borde de las cuñas la compensación de luz falla y salen manchas.
    q = (bordes - [x_min, y_min]) * px_mm  # sup-izq, sup-der, inf-der, inf-izq
    valida = (int(max(q[0, 0], q[3, 0])) + 5, int(max(q[0, 1], q[1, 1])) + 5,
              int(min(q[1, 0], q[2, 0])) - 5, int(min(q[2, 1], q[3, 1])) - 5)
    cfg["escala"]["px_por_mm"] = round(px_mm, 4)
    rect = comun.rectificar(img, cfg)

    paso = cfg["lego"]["paso_stud_mm"]
    print(f"\nEscala rectificada: {px_mm:.3f} px/mm  ({1 / px_mm:.3f} mm/px), igual en todo el tapete")
    print(f"Campo de visión: {ancho_out / px_mm:.0f} x {alto_out / px_mm:.0f} mm")
    print(f"Un stud (paso {paso} mm) ocupa {paso * px_mm:.1f} px")
    print(f"Diámetro de un stud (4,8 mm) ocupa {4.8 * px_mm:.1f} px")

    print("\nAhora arrastra un rectángulo sobre la zona útil del tapete y pulsa ENTER (ESC = toda la zona válida).")
    x, y, rw, rh = cv2.selectROI("regla", rect, showCrosshair=False)
    if rw <= 0 or rh <= 0:
        x, y, rw, rh = 0, 0, ancho_out, alto_out
    # Se recorta a la zona válida (la ROI antigua estaba en coordenadas sin rectificar)
    x0, y0 = max(x, valida[0]), max(y, valida[1])
    x1, y1 = min(x + rw, valida[2]), min(y + rh, valida[3])
    x, y, rw, rh = int(x0), int(y0), int(x1 - x0), int(y1 - y0)
    cfg["roi"].update({"x": x, "y": y, "ancho": rw, "alto": rh})
    print(f"ROI: {rw / px_mm:.0f} x {rh / px_mm:.0f} mm")
    if rw / px_mm < 500 or rh / px_mm < 500:
        print("AVISO: la zona útil NO cubre 500 x 500 mm. Sube la cámara o usa un modo 4:3.")
    comun.guardar_config(cfg)
    print("Guardado en config/config.json. Las fotos de fondo siguen valiendo (se rectifican al cargarlas).")

    # Figuras para la memoria: escala por lado antes de corregir, y vista rectificada con la ROI
    comun.guardar_imagen(comun.ruta("resultados", "figuras", "calibracion_perspectiva.png"), vista)
    hoja = cv2.perspectiveTransform(esq.reshape(-1, 1, 2), escala @ h_mm).astype(np.int32)
    cv2.polylines(rect, [hoja], True, (0, 0, 255), 2)
    cv2.putText(rect, f"{ancho_mm:.0f} x {alto_mm:.0f} mm -> {px_mm:.3f} px/mm",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.rectangle(rect, (int(x), int(y)), (int(x + rw), int(y + rh)), (255, 255, 0), 3)
    comun.guardar_imagen(comun.ruta("resultados", "figuras", "calibracion_escala.png"), rect)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
