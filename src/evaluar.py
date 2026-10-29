"""
evaluar.py - Medida cuantitativa de aciertos y errores (apartado obligatorio).

A) Sobre el dataset etiquetado (datos/dataset/<clase>/):
   - Nivel 1 (detección): en cada foto se compara el nº de objetos detectados
     con el nº de piezas que había (n_piezas, que captura.py guarda en el
     .json de cada foto con las teclas 1-9). Sobrantes = falsos positivos,
     faltantes = piezas perdidas. Es una cota inferior: si en la misma foto
     sobra una y falta otra, se compensan.
   - Nivel 2 (identificación): matrices de confusión de tipo, color y clase.
     Solo entran las fotos cuya detección es correcta (si sobra un objeto no
     se sabe cuál es, y contaría como error de clasificación sin serlo).
     Las fotos sin n_piezas entran todas, como antes.
   OJO: si los umbrales se ajustaron con estas mismas fotos, el resultado es
   optimista. Para la memoria, captura un segundo lote solo para evaluar.

B) Por escena, sobre datos/pruebas/: para cada <escena>.png escribe a mano un
   <escena>.real.json con el inventario real, por ejemplo
       {"2x4_rojo": 2, "1x2_azul": 3}
   Aciertos = piezas que coinciden en clase (por recuento de cada clase, no
   por posición). Una pieza mal clasificada es 1 acierto menos y 1 sobrante,
   no 2 errores.

Salidas: resultados/evaluacion.txt y resultados/figuras/confusion_*.png
"""

import glob
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import comun
import detectar
import segmentacion


def matriz(reales, pred, titulo, path):
    etiquetas = sorted(set(reales) | set(pred))
    idx = {e: i for i, e in enumerate(etiquetas)}
    m = np.zeros((len(etiquetas),) * 2, int)
    for r, p in zip(reales, pred):
        m[idx[r], idx[p]] += 1
    plt.figure(figsize=(1 + 0.6 * len(etiquetas), 1 + 0.6 * len(etiquetas)))
    plt.imshow(m, cmap="Blues")
    for i in range(len(etiquetas)):
        for j in range(len(etiquetas)):
            if m[i, j]:
                plt.text(j, i, m[i, j], ha="center", va="center")
    plt.xticks(range(len(etiquetas)), etiquetas, rotation=45, ha="right")
    plt.yticks(range(len(etiquetas)), etiquetas)
    plt.xlabel("predicho"); plt.ylabel("real")
    acc = np.trace(m) / m.sum() if m.sum() else 0
    plt.title(f"{titulo} - acierto {100 * acc:.1f}%")
    plt.tight_layout(); plt.savefig(path, dpi=120); plt.close()
    return acc


def n_piezas(ruta_png):
    """Nº de piezas anotado al capturar la foto (None si no se anotó)."""
    meta = os.path.splitext(ruta_png)[0] + ".json"
    if not os.path.exists(meta):
        return None
    return comun.cargar_json(meta).get("n_piezas")


def evaluar_dataset(cfg, umbrales, log):
    modelo = segmentacion.cargar_modelo_fondo(cfg)
    R = {"tipo": ([], []), "color": ([], []), "clase": ([], [])}
    errores, fallos_det = [], []
    fotos_n = fotos_ok = esperadas = detectadas = sobran = faltan = fotos_sin_n = 0
    for carpeta in sorted(glob.glob(comun.ruta("datos", "dataset", "*"))):
        if not os.path.isdir(carpeta):
            continue
        clase = os.path.basename(carpeta)
        tipo_r, _, color_r = clase.partition("_")
        for r in sorted(glob.glob(os.path.join(carpeta, "*.png"))):
            _, _, piezas, _ = detectar.analizar(comun.leer_imagen(r), modelo, cfg, umbrales)
            n = n_piezas(r)
            if n is None:
                fotos_sin_n += 1
            else:
                fotos_n += 1; esperadas += n; detectadas += len(piezas)
                sobran += max(0, len(piezas) - n); faltan += max(0, n - len(piezas))
                if len(piezas) != n:
                    fallos_det.append(f"{os.path.basename(r)}: esperadas {n}, detectadas {len(piezas)}")
                    continue
                fotos_ok += 1
            for p in piezas:
                for k, real in (("tipo", tipo_r), ("color", color_r), ("clase", clase)):
                    R[k][0].append(real); R[k][1].append(p[k])
                if p["clase"] != clase:
                    errores.append(f"{os.path.basename(r)}: real {clase} -> {p['clase']}  [{' | '.join(p['traza'])}]")
    if not fotos_n and not fotos_sin_n:
        log.append("A) Dataset vacío.")
        return
    log.append("A) DATASET")
    if fotos_n:
        log.append(f"   Nivel 1 (detección), {fotos_n} fotos con n_piezas anotado:")
        log.append(f"     fotos con recuento exacto: {fotos_ok}/{fotos_n} ({100 * fotos_ok / fotos_n:.0f}%)")
        log.append(f"     piezas esperadas {esperadas}, objetos detectados {detectadas}, "
                   f"sobrantes (falsos positivos) {sobran}, faltantes {faltan}")
        log += ["     " + e for e in fallos_det]
    if fotos_sin_n:
        log.append(f"   AVISO: {fotos_sin_n} fotos sin n_piezas: no miden la detección y "
                   "sus falsos positivos cuentan como errores de clasificación.")
    if not R["clase"][0]:
        log.append("   Nivel 2: ninguna foto con detección correcta.")
        return
    log.append(f"   Nivel 2 (identificación): {len(R['clase'][0])} piezas")
    for k in R:
        acc = matriz(*R[k], f"Confusión {k}", comun.ruta("resultados", "figuras", f"confusion_{k}.png"))
        log.append(f"     acierto {k}: {100 * acc:.1f}%")
    log.append("     Errores:" if errores else "     Sin errores.")
    log += ["       " + e for e in errores]


def evaluar_escenas(cfg, umbrales, log):
    escenas = exactas = tot_real = tot_det = tot_ok = 0
    log.append("\nB) POR ESCENA (datos/pruebas con .real.json)")
    modelo_fijo = segmentacion.cargar_modelo_fondo(cfg) if segmentacion.rutas_fondo(cfg) else None
    for js in sorted(glob.glob(comun.ruta("datos", "pruebas", "*.real.json"))):
        png = js[:-len(".real.json")] + ".png"
        if not os.path.exists(png):
            log.append(f"   {os.path.basename(js)}: falta la imagen {os.path.basename(png)}")
            continue
        with open(js, encoding="utf-8") as fh:
            real = Counter(json.load(fh))
        img = comun.leer_imagen(png)
        modelo = modelo_fijo or segmentacion.cargar_modelo_fondo(cfg, segmentacion.preprocesar(img, cfg))
        _, _, piezas, _ = detectar.analizar(img, modelo, cfg, umbrales)
        # Todo lo detectado cuenta, también lo que el árbol no clasificó (dudoso, irregular...)
        det = Counter(p["clase"] for p in piezas)
        ok = sum(min(n, det[c]) for c, n in real.items())
        n_real, n_det = sum(real.values()), sum(det.values())
        escenas += 1; exactas += (ok == n_real == n_det)
        tot_real += n_real; tot_det += n_det; tot_ok += ok
        estado = "OK" if ok == n_real == n_det else f"FALLO (aciertos {ok}/{n_real}, sobrantes {n_det - ok})"
        log.append(f"   {os.path.basename(png)}: {estado}  real={dict(real)}  detectado={dict(det)}")
    if escenas:
        log.append(f"   Escenas con inventario exacto: {exactas}/{escenas} ({100 * exactas / escenas:.0f}%)")
        log.append(f"   Piezas acertadas: {tot_ok}/{tot_real} reales ({100 * tot_ok / max(1, tot_real):.1f}%); "
                   f"{tot_ok}/{tot_det} de lo detectado es correcto ({100 * tot_ok / max(1, tot_det):.1f}%)")
    else:
        log.append("   No hay escenas etiquetadas. Para cada <escena>.png crea <escena>.real.json con el inventario real.")


def main():
    cfg, umbrales = comun.cargar_config(), comun.cargar_umbrales()
    log = []
    evaluar_dataset(cfg, umbrales, log)
    evaluar_escenas(cfg, umbrales, log)
    texto = "\n".join(log)
    print(texto)
    with open(comun.ruta("resultados", "evaluacion.txt"), "w", encoding="utf-8") as fh:
        fh.write(texto)


if __name__ == "__main__":
    main()
