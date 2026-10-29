"""
detectar.py - Pipeline completo: detección + identificación + inventario.

  Imagen -> preprocesado -> segmentación -> características -> árbol -> inventario

Uso:
  python src/detectar.py --imagen datos/pruebas/escena1.png    (una foto)
  python src/detectar.py --carpeta datos/pruebas               (todas las fotos)
  python src/detectar.py --camara                              (en vivo)
Opciones:  --debug  muestra también la máscara de segmentación

En vivo: ESPACIO congela/descongela, s guarda el resultado, q sale,
         b recaptura el fondo (retira antes todas las piezas del tapete).
Resultados en resultados/: imagen anotada, CSV por pieza e inventario JSON.
"""

import argparse
import csv
import glob
import os
from collections import Counter
from datetime import datetime

import cv2
import numpy as np

import arbol
import caracteristicas
import comun
import segmentacion

COLORES_DIBUJO = {
    "rojo": (0, 0, 255), "naranja": (0, 140, 255), "amarillo": (0, 230, 255),
    "verde": (0, 200, 0), "azul": (255, 80, 0), "morado": (200, 0, 160),
    "negro": (40, 40, 40), "blanco": (255, 255, 255), "gris": (150, 150, 150),
}


def analizar(img, modelo, cfg, umbrales):
    pre = segmentacion.preprocesar(img, cfg)
    mascara, contornos = segmentacion.segmentar(pre, modelo, cfg)
    piezas = []
    for i, c in enumerate(contornos, 1):
        f = caracteristicas.extraer(c, pre, cfg)
        r = arbol.clasificar(f, umbrales, cfg)
        piezas.append({"id": i, "contorno": c, **f, **r})
    return pre, mascara, piezas, inventario(piezas)


def inventario(piezas):
    """Nivel 3: inventario por tipo y por color (tabla tipo x color con sus
    totales). Lo que el árbol no pudo clasificar (borde, irregular, dudoso...)
    se cuenta aparte para no mezclarlo con las piezas identificadas."""
    validas = [p for p in piezas if p["tipo"] not in arbol.NO_CLASIFICADAS]
    tabla = {}
    for p in validas:
        tabla.setdefault(p["tipo"], Counter())[p["color"]] += 1
    return {
        "detectadas": len(piezas),
        "clasificadas": len(validas),
        "por_clase": dict(sorted(Counter(p["clase"] for p in validas).items())),
        "por_tipo": dict(sorted(Counter(p["tipo"] for p in validas).items())),
        "por_color": dict(sorted(Counter(p["color"] for p in validas).items())),
        "tabla": {t: dict(sorted(c.items())) for t, c in sorted(tabla.items())},
        "no_clasificadas": dict(sorted(Counter(p["tipo"] for p in piezas
                                               if p["tipo"] in arbol.NO_CLASIFICADAS).items())),
    }


def lineas_inventario(inv):
    """Resumen corto del inventario, para la imagen anotada."""
    lineas = [f"Detectadas: {inv['detectadas']}  clasificadas: {inv['clasificadas']}"]
    for tipo, colores in inv["tabla"].items():
        lineas.append(f"{tipo} ({inv['por_tipo'][tipo]}): " + ", ".join(f"{c} {n}" for c, n in colores.items()))
    if inv["por_color"]:
        lineas.append("Colores: " + ", ".join(f"{c} {n}" for c, n in inv["por_color"].items()))
    if inv["no_clasificadas"]:
        lineas.append("Sin clasificar: " + ", ".join(f"{t} {n}" for t, n in inv["no_clasificadas"].items()))
    return lineas


def tabla_texto(inv):
    """Tabla tipo x color con totales por fila y columna, para la consola."""
    colores = list(inv["por_color"])
    if not colores:
        return "  (ninguna pieza clasificada)"
    ancho = max(6, *(len(c) for c in colores))
    fila = lambda nombre, celdas, total: f"  {nombre:<7}|" + "".join(f" {x:>{ancho}}" for x in celdas) + f" | {total:>5}"
    out = [fila("tipo", colores, "total"), "  " + "-" * (len(fila("", colores, "")) - 2)]
    for tipo, cuenta in inv["tabla"].items():
        out.append(fila(tipo, [cuenta.get(c, "") for c in colores], inv["por_tipo"][tipo]))
    out.append(fila("total", [inv["por_color"][c] for c in colores], inv["clasificadas"]))
    return "\n".join(out)


def dibujar(pre, piezas, inv):
    v = pre.copy()
    for p in piezas:
        caja = cv2.boxPoints(cv2.minAreaRect(p["contorno"])).astype(np.int32)
        if p["tipo"] in arbol.NO_CLASIFICADAS:
            col, txt = (255, 0, 255), f"{p['id']}:{p['tipo']}"
        else:
            col, txt = COLORES_DIBUJO.get(p["color"], (255, 0, 255)), f"{p['id']}:{p['tipo']} {p['color']}"
        cv2.drawContours(v, [caja], -1, col, 2)
        org = (int(caja[:, 0].min()), max(20, int(caja[:, 1].min()) - 8))  # encima de la pieza
        cv2.putText(v, txt, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(v, txt, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    # Nivel 3: inventario, en un panel tan ancho como la línea más larga
    lineas = lineas_inventario(inv)
    ancho = max(cv2.getTextSize(l, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0][0] for l in lineas)
    cv2.rectangle(v, (8, 8), (28 + ancho, 24 + 28 * len(lineas)), (0, 0, 0), -1)
    for j, l in enumerate(lineas):
        cv2.putText(v, l, (18, 36 + 28 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return v


def guardar_resultado(nombre, vista, piezas, inv):
    base = comun.ruta("resultados", nombre)
    comun.guardar_imagen(base + "_anotada.png", vista)
    campos = [k for k in piezas[0] if k not in ("contorno",)] if piezas else ["id"]
    with open(base + "_piezas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, delimiter=";")
        w.writeheader()
        for p in piezas:
            w.writerow({k: (" | ".join(p[k]) if k == "traza" else p[k]) for k in campos})
    comun.guardar_json(base + "_inventario.json", inv)
    print("Guardado en resultados/:", nombre)


def imprimir(piezas, inv):
    for p in piezas:
        print(f"  #{p['id']:>2} {p['clase']:<22} {p['largo_mm']}x{p['ancho_mm']} {p['unidades']}  "
              f"studs {p['studs_ancho']}x{p['studs_largo']}  solidez={p['solidez']}  "
              f"H={p['H']} S={p['S']:.0f} V={p['V']:.0f}")
    print(f"  INVENTARIO: {inv['detectadas']} detectadas, {inv['clasificadas']} clasificadas")
    print(tabla_texto(inv))
    if inv["no_clasificadas"]:
        print("  Sin clasificar:", inv["no_clasificadas"])


def modo_imagen(rutas, cfg, umbrales, debug):
    # Con fotos de fondo el modelo se carga una vez; sin ellas se estima de cada imagen
    modelo_fijo = segmentacion.cargar_modelo_fondo(cfg) if segmentacion.rutas_fondo(cfg) else None
    for r in rutas:
        img = comun.leer_imagen(r)
        modelo = modelo_fijo or segmentacion.cargar_modelo_fondo(cfg, segmentacion.preprocesar(img, cfg))
        pre, mascara, piezas, inv = analizar(img, modelo, cfg, umbrales)
        print(os.path.basename(r))
        imprimir(piezas, inv)
        vista = dibujar(pre, piezas, inv)
        guardar_resultado(os.path.splitext(os.path.basename(r))[0], vista, piezas, inv)
        if debug:
            comun.guardar_imagen(comun.ruta("resultados", os.path.splitext(os.path.basename(r))[0] + "_mascara.png"), mascara)
        cv2.namedWindow("resultado", cv2.WINDOW_NORMAL)
        cv2.imshow("resultado", vista)
        if debug:
            cv2.namedWindow("mascara", cv2.WINDOW_NORMAL)
            cv2.imshow("mascara", mascara)
        if (cv2.waitKey(0) & 0xFF) == ord("q"):
            break
    cv2.destroyAllWindows()


def modo_camara(cfg, umbrales, debug):
    cap = comun.abrir_camara(cfg["camara"])
    modelo = segmentacion.cargar_modelo_fondo(cfg)  # en vivo exige fondo.png
    cv2.namedWindow("resultado", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("resultado", 1280, 720)
    congelado, ultimo = False, None
    while True:
        if not congelado:
            ok, img = cap.read()
            if not ok:
                break
            ultimo = analizar(img, modelo, cfg, umbrales)
        pre, mascara, piezas, inv = ultimo
        vista = dibujar(pre, piezas, inv)
        cv2.imshow("resultado", vista)
        if debug:
            cv2.imshow("mascara", mascara)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        elif k == ord(" "):
            congelado = not congelado
            if congelado:
                imprimir(piezas, inv)
        elif k == ord("s"):
            guardar_resultado("vivo_" + datetime.now().strftime("%Y%m%d_%H%M%S"), vista, piezas, inv)
        elif k == ord("b"):
            # La luz del examen no será la de casa: fondo nuevo sin salir del programa
            print("Capturando el fondo (el tapete debe estar VACÍO)...")
            segmentacion.guardar_fondo(comun.leer_fotogramas(cap, cfg["segmentacion"]["fondo_fotogramas"]), cfg)
            modelo = segmentacion.cargar_modelo_fondo(cfg)
            congelado = False
            print("Fondo actualizado.")
    cap.release()
    cv2.destroyAllWindows()


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--imagen")
    g.add_argument("--carpeta")
    g.add_argument("--camara", action="store_true")
    p.add_argument("--debug", action="store_true")
    a = p.parse_args()

    cfg, umbrales = comun.cargar_config(), comun.cargar_umbrales()
    if not cfg["escala"]["px_por_mm"]:
        print("AVISO: escala sin calibrar (ejecuta calibrar_escala.py). Las medidas saldrán en píxeles y el tipo como 'sin_escala'.")
    if a.camara:
        modo_camara(cfg, umbrales, a.debug)
    else:
        rutas = [a.imagen] if a.imagen else sorted(glob.glob(os.path.join(a.carpeta, "*.png")) + glob.glob(os.path.join(a.carpeta, "*.jpg")))
        modo_imagen(rutas, cfg, umbrales, a.debug)


if __name__ == "__main__":
    main()
