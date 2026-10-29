"""
medir_dataset.py - Mide las características de todas las piezas del dataset y
genera las gráficas que justifican cada umbral del árbol.

Estructura esperada (la crea captura.py --destino dataset --clase ...):
  datos/dataset/2x4_rojo/*.png   (una o varias piezas de esa clase por foto)
  datos/dataset/1x2_azul/*.png
  ...
El nombre de carpeta es la etiqueta real: <tipo>_<color>.
Las detecciones que no superan los nodos de validez del árbol (tocan el borde
o tienen solidez < solidez_min) salen en validez_solidez.png pero no entran
en el resumen, ni en las gráficas de umbrales, ni en el sesgo de borde.

Salidas:
  resultados/caracteristicas.csv          una fila por pieza medida
  resultados/resumen_por_clase.csv         media, desviación, mín y máx por clase
  resultados/figuras/hist_fondo.png        justificación de k_sigma (segmentación)
  resultados/figuras/validez_solidez.png   justificación de solidez_min (nodo N1)
  resultados/figuras/studs.png             justificación de la rama TIPO
  resultados/figuras/color_HS.png          justificación de la rama COLOR
  resultados/figuras/<caracteristica>.png  distribución por clase de cada característica
"""

import csv
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import caracteristicas
import comun
import segmentacion

NUMERICAS = ["area_mm2", "perimetro_mm", "circularidad", "solidez", "largo_mm", "ancho_mm",
             "aspecto", "studs_largo", "studs_ancho", "num_studs", "H", "S", "V", "L", "a", "b"]


def medir(cfg, umbrales):
    filas = []
    smin = umbrales["validez"]["solidez_min"]
    modelo = segmentacion.cargar_modelo_fondo(cfg)
    for carpeta in sorted(glob.glob(comun.ruta("datos", "dataset", "*"))):
        if not os.path.isdir(carpeta):
            continue
        clase = os.path.basename(carpeta)
        tipo_real, _, color_real = clase.partition("_")
        for r in sorted(glob.glob(os.path.join(carpeta, "*.png"))):
            pre = segmentacion.preprocesar(comun.leer_imagen(r), cfg)
            _, contornos = segmentacion.segmentar(pre, modelo, cfg)
            for c in contornos:
                f = caracteristicas.extraer(c, pre, cfg)
                filas.append({"imagen": os.path.basename(r), "clase_real": clase,
                              "tipo_real": tipo_real, "color_real": color_real,
                              "valida": not f["toca_borde"] and f["solidez"] >= smin, **f})
        sub = [f for f in filas if f["clase_real"] == clase]
        print(f"{clase}: {sum(f['valida'] for f in sub)} piezas válidas de {len(sub)} detecciones")
    return filas, modelo


def guardar_csv(filas, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(filas)


def resumen(filas):
    out = []
    for clase in sorted({f["clase_real"] for f in filas}):
        sub = [f for f in filas if f["clase_real"] == clase]
        fila = {"clase": clase, "n": len(sub)}
        for k in NUMERICAS:
            v = np.array([s[k] for s in sub], dtype=float)
            fila.update({f"{k}_media": round(v.mean(), 2), f"{k}_std": round(v.std(), 2),
                         f"{k}_min": round(v.min(), 2), f"{k}_max": round(v.max(), 2)})
        out.append(fila)
    return out


def figuras(filas, modelo, cfg, umbrales):
    fig_dir = comun.ruta("resultados", "figuras")
    os.makedirs(fig_dir, exist_ok=True)

    # 1. Segmentación: distancias del fondo vacío vs umbral
    k = cfg["segmentacion"]["k_sigma"]
    d = modelo.dist_fondo.ravel()
    plt.figure(figsize=(7, 4))
    plt.hist(d, bins=200, range=(0, max(k * 2, np.percentile(d, 99.99))), log=True, color="gray")
    plt.axvline(k, color="r", label=f"k_sigma = {k}")
    plt.title(f"Distancia al modelo de fondo en el tapete vacío\n{100 * (d > k).mean():.4f}% de píxeles de fondo superan el umbral")
    plt.xlabel("distancia (nº de sigmas)"); plt.ylabel("nº píxeles (log)"); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "hist_fondo.png"), dpi=130); plt.close()

    if not filas:
        return

    # 2. Nodo de validez N1: solidez de todo lo detectado (piezas y manchas)
    smin = umbrales["validez"]["solidez_min"]
    sol = [f["solidez"] for f in filas if not f["toca_borde"]]
    plt.figure(figsize=(7, 4))
    plt.hist(sol, bins=40, range=(0, 1), color="gray")
    plt.axvline(smin, color="r", label=f"solidez_min = {smin}")
    plt.title(f"Solidez de todas las detecciones (n={len(sol)})\n"
              f"{sum(s < smin for s in sol)} por debajo del umbral -> 'irregular'")
    plt.xlabel("solidez = área / área envolvente convexa"); plt.ylabel("nº detecciones")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "validez_solidez.png"), dpi=130); plt.close()

    filas = [f for f in filas if f["valida"]]
    if not filas:
        return
    clases_tipo = sorted({f["tipo_real"] for f in filas})
    clases_color = sorted({f["color_real"] for f in filas})

    # 3. Rama TIPO: rejilla medida en studs, por tipo real
    plt.figure(figsize=(6, 6))
    for t in clases_tipo:
        sub = [f for f in filas if f["tipo_real"] == t]
        plt.scatter([s["studs_largo"] for s in sub], [s["studs_ancho"] for s in sub], label=t, s=18)
    tol = umbrales["tipos"]["tolerancia_studs"]
    for n in range(1, 9):
        plt.axvspan(n - tol, n + tol, color="g", alpha=0.06)
        plt.axhspan(n - tol, n + tol, color="g", alpha=0.06)
    plt.xlabel("largo (studs)"); plt.ylabel("ancho (studs)")
    plt.title(f"Rama TIPO: rejilla medida (bandas verdes = ±{tol} studs)")
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "studs.png"), dpi=130); plt.close()

    # 4. Rama COLOR: H frente a S, por color real, con los cortes de tono actuales
    c = umbrales["color"]
    plt.figure(figsize=(8, 5))
    for col in clases_color:
        sub = [f for f in filas if f["color_real"] == col]
        plt.scatter([s["H"] for s in sub], [s["S"] for s in sub], label=col, s=18)
    plt.axhline(c["saturacion_min_cromatico"], color="k", ls="--", label="S mín. cromático")
    inicio = 0
    for limite, nombre in c["cortes_tono"]:
        plt.axvline(limite, color="gray", lw=0.5)
        plt.text((inicio + limite) / 2, plt.ylim()[1], nombre, ha="center", va="bottom", fontsize=7, rotation=90)
        inicio = limite
    plt.xlabel("tono H (0-180)"); plt.ylabel("saturación S"); plt.xlim(0, 180)
    plt.title("Rama COLOR: tono y saturación por color real", pad=40); plt.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(os.path.join(fig_dir, "color_HS.png"), dpi=130); plt.close()

    # 5. Distribución de cada característica por clase
    clases = sorted({f["clase_real"] for f in filas})
    for k_ in NUMERICAS:
        plt.figure(figsize=(max(6, 0.6 * len(clases)), 4))
        datos = [[f[k_] for f in filas if f["clase_real"] == cl] for cl in clases]
        plt.boxplot(datos, showfliers=True)
        plt.xticks(range(1, len(clases) + 1), clases, rotation=45, ha="right"); plt.title(k_); plt.grid(alpha=0.3, axis="y")
        plt.tight_layout(); plt.savefig(os.path.join(fig_dir, f"{k_}.png"), dpi=110); plt.close()


def sesgo_borde(filas, cfg):
    """Compara la medida con la nominal LEGO (N*8 - 0,2 mm) para estimar cuánto
    mide de más la silueta segmentada. Devuelve la corrección sugerida en mm."""
    corr_actual = cfg["lego"].get("correccion_borde_mm", 0.0)
    difs = []
    for f in filas:
        try:
            n, m = (int(x) for x in f["tipo_real"].lower().split("x"))
        except ValueError:
            continue
        nom_a, nom_l = sorted((n, m))
        # se suma la corrección ya aplicada para obtener la medida bruta
        difs.append(f["ancho_mm"] + corr_actual - (nom_a * 8 - 0.2))
        difs.append(f["largo_mm"] + corr_actual - (nom_l * 8 - 0.2))
    if not difs:
        return None
    d = np.array(difs)
    print(f"\nSesgo de borde: la silueta mide {d.mean():+.2f} mm de más (desv. {d.std():.2f} mm, n={len(d)})")
    print(f"  -> correccion_borde_mm sugerida = {d.mean():.2f}  (actual: {corr_actual})")
    return round(float(d.mean()), 2)


def main():
    cfg, umbrales = comun.cargar_config(), comun.cargar_umbrales()
    if not cfg["escala"]["px_por_mm"]:
        print("AVISO: escala sin calibrar; las medidas geométricas saldrán en píxeles.")
    filas, modelo = medir(cfg, umbrales)
    figuras(filas, modelo, cfg, umbrales)
    validas = [f for f in filas if f["valida"]]
    if not validas:
        print("No hay piezas válidas en datos/dataset/. Captura con: python src/captura.py --destino dataset --clase 2x4_rojo")
        return
    guardar_csv(filas, comun.ruta("resultados", "caracteristicas.csv"))
    guardar_csv(resumen(validas), comun.ruta("resultados", "resumen_por_clase.csv"))
    sug = sesgo_borde(validas, cfg)
    if sug is not None and abs(sug - cfg["lego"].get("correccion_borde_mm", 0.0)) > 0.1:
        if input("¿Guardar esa corrección en config.json? [s/N] ").strip().lower() == "s":
            c = comun.cargar_config(); c["lego"]["correccion_borde_mm"] = sug; comun.guardar_config(c)
            print("Guardada. Vuelve a ejecutar medir_dataset.py para regenerar las gráficas.")
    print(f"{len(validas)} piezas válidas de {len(filas)} detecciones. CSV y figuras en resultados/")


if __name__ == "__main__":
    main()
