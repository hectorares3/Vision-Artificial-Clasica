"""
arbol.py - Nivel 2 (identificación): árbol de decisión explícito.

Clase final = TIPO (geometría) + COLOR -> dos ramas independientes del árbol.

Rama TIPO
  N0  ¿la silueta toca el borde de la zona útil?      sí -> 'borde' (pieza cortada)
  N1  ¿solidez >= solidez_min?                        no -> 'irregular' (mancha del
                                                             fondo o piezas juntas)
  N2  ¿la escala está calibrada?                      no -> 'sin_escala'
  N3  ¿studs_largo y studs_ancho están a menos de
       tolerancia_studs de un entero?                  no -> 'dudoso'
  N4  N x M = (round(ancho), round(largo)) en studs
  N5  ¿N x M está en la lista de tipos aceptados?      no -> 'desconocido'

Rama COLOR
  C1  S < saturacion_min_cromatico ?  sí -> acromático:
        C1a  V < valor_max_negro  -> negro
        C1b  V > valor_min_blanco -> blanco
        C1c  resto                -> gris
  C2  cromático: cortes de tono en orden (H < 7 -> rojo, H < 18 -> naranja...)

Todos los umbrales viven en config/umbrales.json y se justifican con las
gráficas que genera src/medir_dataset.py. Cada clasificación devuelve la
traza de nodos recorridos para poder enseñarla en la memoria y en el vídeo.
"""

# Salidas de la rama TIPO que no son un tipo de pieza: van aparte en el inventario
NO_CLASIFICADAS = ("borde", "irregular", "sin_escala", "dudoso", "desconocido")


def clasificar_tipo(f, u, escala_ok):
    traza = []
    if f["toca_borde"]:
        traza.append("N0: toca el borde de la zona útil")
        return "borde", traza
    smin = u["validez"]["solidez_min"]
    traza.append(f"N1: solidez {f['solidez']:.2f} {'>=' if f['solidez'] >= smin else '<'} {smin}")
    if f["solidez"] < smin:
        return "irregular", traza
    if not escala_ok:
        traza.append("N2: escala no calibrada")
        return "sin_escala", traza
    tol = u["tipos"]["tolerancia_studs"]
    el, ea = f["studs_largo"], f["studs_ancho"]
    nl, na = max(1, round(el)), max(1, round(ea))
    err = max(abs(el - nl), abs(ea - na))
    traza.append(f"N3: error rejilla {err:.2f} {'<=' if err <= tol else '>'} {tol}")
    if err > tol:
        return "dudoso", traza
    tipo = f"{na}x{nl}"
    traza.append(f"N4: rejilla {tipo}")
    if tipo not in u["tipos"]["aceptados"]:
        traza.append("N5: tipo no aceptado")
        return "desconocido", traza
    traza.append("N5: tipo aceptado")
    return tipo, traza


def clasificar_color(f, u):
    c = u["color"]
    traza = []
    if f["S"] < c["saturacion_min_cromatico"]:
        traza.append(f"C1: S={f['S']:.0f} < {c['saturacion_min_cromatico']} -> acromático")
        if f["V"] < c["valor_max_negro"]:
            traza.append(f"C1a: V={f['V']:.0f} < {c['valor_max_negro']}")
            return "negro", traza
        if f["V"] > c["valor_min_blanco"]:
            traza.append(f"C1b: V={f['V']:.0f} > {c['valor_min_blanco']}")
            return "blanco", traza
        traza.append("C1c: gris")
        return "gris", traza
    traza.append(f"C1: S={f['S']:.0f} >= {c['saturacion_min_cromatico']} -> cromático")
    h = f["H"]
    for limite, nombre in c["cortes_tono"]:
        if h < limite:
            traza.append(f"C2: H={h:.1f} < {limite} -> {nombre}")
            return nombre, traza
    # No debería ocurrir: H está en [0, 180) y el último corte es 180
    traza.append(f"C2: H={h:.1f} fuera de los cortes")
    return "color_desconocido", traza


def clasificar(f, umbrales, cfg):
    tipo, t1 = clasificar_tipo(f, umbrales, bool(cfg["escala"]["px_por_mm"]))
    color, t2 = clasificar_color(f, umbrales)
    return {"tipo": tipo, "color": color, "clase": f"{tipo}_{color}", "traza": t1 + t2}


def arbol_mermaid(umbrales):
    """Diagrama del árbol con los umbrales actuales, para pegar en la memoria
    (mermaid.live lo convierte en imagen)."""
    t, c, v = umbrales["tipos"], umbrales["color"], umbrales["validez"]
    lineas = [
        "flowchart TD",
        "  P[Pieza segmentada] --> T{{Rama TIPO}}",
        "  P --> C{{Rama COLOR}}",
        '  T --> N0{"¿toca el borde?"}',
        "  N0 -- sí --> B[borde]",
        f'  N0 -- no --> N1{{"solidez >= {v["solidez_min"]}?"}}',
        "  N1 -- no --> IR[irregular]",
        f'  N1 -- sí --> N3{{"error rejilla <= {t["tolerancia_studs"]}?"}}',
        "  N3 -- no --> D[dudoso]",
        '  N3 -- sí --> N4["N x M = round(studs)"]',
        f'  N4 --> N5{{"N x M en {", ".join(t["aceptados"])}?"}}',
        "  N5 -- no --> X[desconocido]",
        "  N5 -- sí --> TIPO[tipo N x M]",
        '  TIPO --> CL["clase = tipo + color"]',
        f'  C --> C1{{"S < {c["saturacion_min_cromatico"]}?"}}',
        f'  C1 -- sí --> C1a{{"V < {c["valor_max_negro"]}?"}}',
        "  C1a -- sí --> NEG[negro]",
        f'  C1a -- no --> C1b{{"V > {c["valor_min_blanco"]}?"}}',
        "  C1b -- sí --> BLA[blanco]",
        "  C1b -- no --> GRI[gris]",
        "  C1 -- no --> H0",
        "  NEG & BLA & GRI -.-> CL",
    ]
    # Cortes de tono como cadena de nodos binarios: H < límite ? color : siguiente
    cortes = c["cortes_tono"]
    for i, (limite, nombre) in enumerate(cortes):
        if i == len(cortes) - 1:
            lineas.append(f"  H{i}[{nombre}] -.-> CL")
            break
        lineas += [f'  H{i}{{"H < {limite}?"}}',
                   f"  H{i} -- sí --> HC{i}[{nombre}]",
                   f"  H{i} -- no --> H{i + 1}",
                   f"  HC{i} -.-> CL"]
    return "\n".join(lineas)


if __name__ == "__main__":
    import comun
    print(arbol_mermaid(comun.cargar_umbrales()))
