"""
captura.py - Vista previa en vivo y captura de imágenes para el proyecto LEGO.

Uso:
  python src/captura.py                          -> guarda en datos/pruebas
  python src/captura.py --destino dataset --clase 2x4_rojo
                                                 -> guarda en datos/dataset/2x4_rojo
  python src/captura.py --destino calibracion    -> guarda en datos/calibracion

Teclas (la ventana de la cámara debe estar activa: haz clic en ella primero):
  s  o CLIC IZQUIERDO en la imagen: guardar captura (PNG + JSON con los ajustes reales de la cámara)
  1-9  nº de piezas que hay en el tapete (se guarda en el JSON; evaluar.py lo usa
       para medir la detección)          0  sin anotar
  f  guardar FONDO (tapete vacío): varias fotos seguidas -> datos/calibracion/fondo/
  r  guardar como REGLA (tapete + hoja A4) -> datos/calibracion/regla.png
  k  guardar exposición/balance/ganancia actuales en config/config.json
  m  alternar AUTO <-> MANUAL (para ver por qué hay que usar manual)
  + / -   exposición     w / e   temperatura de balance de blancos     a / d   ganancia
  z  zebra: píxeles quemados en magenta    g  rejilla y cruz central
  c  panel del driver de la cámara (enfoque manual, etc.)
  q  salir
"""

import argparse
import os
import re
import time
from datetime import datetime

import cv2

import comun
import segmentacion

p = argparse.ArgumentParser()
p.add_argument("--destino", default="pruebas", choices=["pruebas", "dataset", "calibracion"])
p.add_argument("--clase", default=None, help="Nombre de clase si destino=dataset, p. ej. 2x4_rojo")
args = p.parse_args()

PATRON_CLASE = re.compile(r"^\d+x\d+_[a-záéíóúñ]+$")
if args.destino == "dataset":
    # El nombre de la carpeta es la etiqueta real de las fotos: tiene que ser tipo_color
    while not args.clase or not PATRON_CLASE.match(args.clase.strip().lower()):
        if args.clase:
            print(f"'{args.clase}' no vale. Formato: <ancho>x<largo>_<color>, por ejemplo 2x4_rojo o 1x2_azul")
        args.clase = input("Clase de las piezas que vas a fotografiar (p. ej. 2x4_rojo): ")
    args.clase = args.clase.strip().lower()
    # El árbol nombra el tipo como lado corto x lado largo: 4x2 sería siempre "error"
    rejilla, _, color = args.clase.partition("_")
    args.clase = "x".join(sorted(rejilla.split("x"), key=int)) + "_" + color

cfg = comun.cargar_config()
cam = cfg["camara"]
carpeta = comun.ruta("datos", args.destino, *( [args.clase] if args.clase else [] ))
os.makedirs(carpeta, exist_ok=True)


def ayudas(img, zebra, rejilla):
    v = img.copy()
    if zebra:
        v[(img >= 250).any(axis=2)] = (255, 0, 255)
    if rejilla:
        h, w = v.shape[:2]
        for i in (1, 2):
            cv2.line(v, (w * i // 3, 0), (w * i // 3, h), (255, 255, 255), 1)
            cv2.line(v, (0, h * i // 3), (w, h * i // 3), (255, 255, 255), 1)
        cv2.drawMarker(v, (w // 2, h // 2), (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
    return v


def guardar_meta(ruta_png, cap, manual, media, pct, n_piezas=None):
    meta = comun.propiedades_camara(cap)
    meta.update({"modo": "manual" if manual else "auto", "luz_media": round(media, 1),
                 "pct_quemado": round(pct, 3), "fecha": datetime.now().isoformat()})
    if n_piezas is not None:
        meta["n_piezas"] = n_piezas
    comun.guardar_json(os.path.splitext(ruta_png)[0] + ".json", meta)


def guardar(frame, ruta_png, cap, manual, media, pct, n_piezas=None):
    comun.guardar_imagen(ruta_png, frame)
    guardar_meta(ruta_png, cap, manual, media, pct, n_piezas)
    print("Guardada:", ruta_png)


pedir_guardado = False


def clic(evento, x, y, flags, param):
    global pedir_guardado
    if evento == cv2.EVENT_LBUTTONDOWN:
        pedir_guardado = True


def main():
    global pedir_guardado
    cap = comun.abrir_camara(cam)
    manual, zebra, rejilla = True, True, True
    print("Cámara abierta:", comun.propiedades_camara(cap))
    print("Guardando en:", carpeta)
    cv2.namedWindow("captura", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("captura", 1280, 720)
    cv2.setMouseCallback("captura", clic)
    n_guardadas = len([f for f in os.listdir(carpeta) if f.endswith(".png")])
    aviso_hasta, aviso = 0.0, ""
    n_piezas = None
    if cam.get("ganancia") is None:
        cam["ganancia"] = int(cap.get(cv2.CAP_PROP_GAIN))

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Fallo leyendo fotograma.")
            break
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        media = float(gris.mean())
        pct = 100.0 * float((frame >= 250).any(axis=2).mean())

        v = ayudas(frame, zebra, rejilla)
        t = (f"{'MANUAL' if manual else 'AUTO'} exp={cam['exposicion']} wb={cam['wb_temperatura']}K "
             f"gan={cam['ganancia']} luz={media:.0f} quemado={pct:.2f}% {frame.shape[1]}x{frame.shape[0]} "
             f"-> {args.destino}{'/' + args.clase if args.clase else ''}")
        cv2.putText(v, t, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(v, t, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        t2 = (f"Guardadas en esta carpeta: {n_guardadas}   "
              f"piezas en la foto: {n_piezas if n_piezas is not None else '-'} (1-9)   (s o clic = guardar, q = salir)")
        cv2.putText(v, t2, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(v, t2, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        if time.time() < aviso_hasta:
            h_, w_ = v.shape[:2]
            cv2.rectangle(v, (0, 0), (w_ - 1, h_ - 1), (0, 255, 0), 25)
            cv2.putText(v, aviso, (w_ // 2 - 330, h_ // 2), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 0), 12)
            cv2.putText(v, aviso, (w_ // 2 - 330, h_ // 2), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 0), 5)
        cv2.imshow("captura", v)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        elif k == ord("s") or pedir_guardado:
            pedir_guardado = False
            sello = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            pref = args.clase or args.destino
            guardar(frame, os.path.join(carpeta, f"{pref}_{sello}.png"), cap, manual, media, pct, n_piezas)
            n_guardadas += 1
            aviso, aviso_hasta = f"GUARDADA ({n_guardadas})", time.time() + 0.8
        elif ord("0") <= k <= ord("9"):
            n_piezas = (k - ord("0")) or None
        elif k == ord("f"):
            fotos = comun.leer_fotogramas(cap, cfg["segmentacion"]["fondo_fotogramas"])
            segmentacion.guardar_fondo(fotos, cfg)
            guardar_meta(comun.ruta(cfg["segmentacion"]["fondo_imagen"]), cap, manual, media, pct)
            print(f"Fondo guardado: {len(fotos)} fotos en {cfg['segmentacion']['fondo_carpeta']}")
            aviso, aviso_hasta = "FONDO GUARDADO", time.time() + 1.2
        elif k == ord("r"):
            guardar(frame, comun.ruta("datos", "calibracion", "regla.png"), cap, manual, media, pct)
            aviso, aviso_hasta = "REGLA GUARDADA", time.time() + 1.2
        elif k == ord("k"):
            c = comun.cargar_config()
            c["camara"]["exposicion"] = cam["exposicion"]
            c["camara"]["wb_temperatura"] = cam["wb_temperatura"]
            c["camara"]["ganancia"] = cam["ganancia"]
            comun.guardar_config(c)
            print("Ajustes de cámara guardados en config.json")
        elif k == ord("m"):
            manual = not manual
            comun.fijar_manual(cap, cam) if manual else comun.fijar_auto(cap)
        elif k in (ord("+"), ord("=")) and manual:
            cam["exposicion"] = min(cam["exposicion"] + 1, -1)
            cap.set(cv2.CAP_PROP_EXPOSURE, cam["exposicion"])
        elif k == ord("-") and manual:
            cam["exposicion"] = max(cam["exposicion"] - 1, -13)
            cap.set(cv2.CAP_PROP_EXPOSURE, cam["exposicion"])
        elif k == ord("w") and manual:
            cam["wb_temperatura"] = max(cam["wb_temperatura"] - 250, 2000)
            cap.set(cv2.CAP_PROP_WB_TEMPERATURE, cam["wb_temperatura"])
        elif k == ord("e") and manual:
            cam["wb_temperatura"] = min(cam["wb_temperatura"] + 250, 7500)
            cap.set(cv2.CAP_PROP_WB_TEMPERATURE, cam["wb_temperatura"])
        elif k == ord("a") and manual:
            cam["ganancia"] = max(cam["ganancia"] - 16, 0)
            cap.set(cv2.CAP_PROP_GAIN, cam["ganancia"])
        elif k == ord("d") and manual:
            cam["ganancia"] = min(cam["ganancia"] + 16, 255)
            cap.set(cv2.CAP_PROP_GAIN, cam["ganancia"])
        elif k == ord("z"):
            zebra = not zebra
        elif k == ord("g"):
            rejilla = not rejilla
        elif k == ord("c"):
            cap.set(cv2.CAP_PROP_SETTINGS, 1)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
