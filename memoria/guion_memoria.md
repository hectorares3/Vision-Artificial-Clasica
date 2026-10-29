# Guion del trabajo escrito

Portada: título, nombre, **enlace al vídeo de YouTube (cuenta de la universidad)**.

1. **Contextualización y requisitos**: reto LEGO, 4–6 tipos × varios colores, clase = tipo + color, tres niveles.
2. **Montaje físico**: modelo de webcam, altura, caja de cartón, iluminación, foto del montaje.
   - Figuras: `calibracion_perspectiva.png` (escala de cada lado de la hoja antes de corregir: prueba de la inclinación) y `calibracion_escala.png` (vista rectificada con la ROI).
   - Tabla: px/mm, campo de visión en mm, px por stud, px por diámetro de stud → justifica la resolución. Indicar si la zona útil llega a 500 × 500 mm.
   - Ajustes de cámara fijos, ganancia incluida (copiar del JSON de captura), y por qué se fijan (comparar AUTO vs MANUAL).
3. **Diagrama del pipeline**.
4. **Segmentación**: homografía, modelo de fondo en Lab con σ local, compensación de deriva de luz, k_sigma, morfología, área mínima.
   - Figura: `hist_fondo.png` + ejemplo de máscara (`detectar.py --debug`).
   - Experimento: nº de falsos positivos con σ global y sin compensación frente al método final, en las mismas fotos.
5. **Tabla de características**: nombre, fórmula, unidad, para qué sirve (ver docstring de `caracteristicas.py`).
6. **Árbol de decisión**: `python src/arbol.py` genera el diagrama Mermaid con los umbrales actuales (pegarlo en mermaid.live).
7. **Justificación de umbrales**: una gráfica por nodo:
   - solidez mínima (nodo de validez) → `validez_solidez.png`
   - tolerancia de rejilla → `studs.png`
   - corrección de borde → salida de `medir_dataset.py`
   - saturación mínima y cortes de tono → `color_HS.png`, `S.png`, `H.png`
8. **Resultados**: escenas de prueba, imágenes anotadas con el inventario tipo × color.
9. **Medida cuantitativa**: `evaluacion.txt` + `confusion_*.png`. Nivel 1 (detección: sobrantes y faltantes) y Nivel 2 (clasificación) por separado. Separar dataset de ajuste y lote de evaluación.
10. **Código**: carpeta `src/` comentada.

Nota: la convocatoria exige revisar críticamente lo que genere el LLM. Cada número de la memoria debe salir de `resultados/`.
