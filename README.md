# Parcial de Visión Artificial Clásica: Reto LEGO

Sistema de visión clásica que detecta piezas LEGO sobre un tapete verde, las clasifica por **tipo geométrico + color** con un árbol de decisión explícito y genera el **inventario** de la escena.

```
Imagen RGB → rectificación + preprocesado → segmentación → características → árbol de decisión → clase → inventario
```

## Estructura

```
parcial-lego/
├── 0_instalar.bat … 7_evaluar.bat   ← doble clic, en orden
├── config/
│   ├── config.json      cámara, escala, ROI, segmentación (se rellena al calibrar)
│   └── umbrales.json    umbrales del árbol de decisión (provisionales hasta medir)
├── src/
│   ├── comun.py             rutas, configuración, apertura de cámara en manual
│   ├── captura.py           vista previa en vivo y captura de fotos
│   ├── calibrar_escala.py   homografía (vista cenital), px/mm y zona útil a partir de la hoja A4
│   ├── segmentacion.py      Nivel 1: sustracción de fondo en Lab
│   ├── caracteristicas.py   área, perímetro, circularidad, solidez, rejilla en studs, color…
│   ├── arbol.py             Nivel 2: árbol de decisión (validez + tipo + color)
│   ├── detectar.py          pipeline completo + Nivel 3: inventario tipo × color
│   ├── medir_dataset.py     mide el dataset y genera las gráficas de umbrales
│   └── evaluar.py           matrices de confusión y aciertos por escena
├── datos/
│   ├── calibracion/   fondo/ (fotos del tapete vacío), fondo.png (la primera) y regla.png
│   ├── dataset/       una subcarpeta por clase: 2x4_rojo/, 1x2_azul/…
│   └── pruebas/       escenas mezcladas + su inventario real (.real.json)
├── resultados/        CSV, imágenes anotadas, evaluación
│   └── figuras/       gráficas para la memoria
└── memoria/           guion del trabajo escrito y figuras propias
```

## Flujo de trabajo

| Paso | Script | Qué haces |
|---|---|---|
| 0 | `0_instalar.bat` | Solo la primera vez. Necesita Python 3.10+ instalado desde python.org. |
| 1 | `1_capturar_calibracion.bat` | Ajusta luz, exposición (`+`/`-`) y ganancia (`a`/`d`): con el tapete vacío, `luz` en torno a 80–120 y sin magenta (quemado). Primero más luz y luego menos ganancia. Guarda con `k`. Tapete **vacío** → `f` (toma varias fotos seguidas). Con una **hoja A4** plana y sin esquinas dobladas → `r`. |
| 2 | `2_calibrar_escala.bat` | Clic en las 4 esquinas de la hoja, Enter (A4) y arrastra la zona útil **solo sobre el tapete**. Corrige la inclinación de la cámara (homografía) y da px/mm y px por stud: es la **justificación de la resolución**. |
| 3 | `3_capturar_dataset.bat` | Una ejecución por clase (`2x4_rojo`…). Unas 10 fotos por clase con 3–5 piezas iguales, en posiciones y giros distintos y **también en las esquinas**. Antes de cada foto pulsa el **número de piezas** (`1`–`9`): sirve para medir la detección. |
| 4 | `4_medir_dataset.bat` | CSV + gráficas. Propone `correccion_borde_mm`. Con las gráficas se ajusta `umbrales.json`. |
| 5 | `5_detectar_en_vivo.bat` | Sistema completo en vivo, con la máscara de segmentación al lado. Con el tapete vacío, `b` recaptura el fondo: hazlo al empezar cualquier sesión, sobre todo en el examen. |
| 6 | `6_capturar_escenas_prueba.bat` | Escenas mezcladas. Para cada `X.png`, crea a mano `X.real.json`, por ejemplo `{"2x4_rojo": 2, "1x2_azul": 1}`. |
| 7 | `7_evaluar.bat` | Aciertos y errores, para la memoria. |

**Si cambias la luz, la resolución, la altura de la cámara o la ROI**, repite los pasos 1 y 2 (nuevo fondo y nueva escala).

## Cómo decide

**Rectificación.** Con las 4 esquinas de la hoja A4 se calcula una homografía que convierte la imagen en una vista cenital con la misma escala en todo el tapete. Sin ella, la cámara inclinada daba 3,15 px/mm arriba y ~3,99 abajo, y un 2x4 cambiaba de tamaño según dónde estuviera.

**Segmentación.** Con varias fotos del tapete vacío se modela, en cada píxel, el color esperado del fieltro y su ruido (σ local: el ruido crece con el brillo). Antes de umbralizar se resta la deriva lenta de luz entre el fondo y la escena. Un píxel es pieza si su distancia en Lab al modelo supera `k_sigma` σ locales. `hist_fondo.png` muestra cuántos píxeles de fondo superarían ese umbral.

**Validez.** Antes de clasificar, el árbol descarta lo que no es una pieza aislada y completa: siluetas que tocan el borde de la zona útil (`borde`) y siluetas poco convexas (`solidez < solidez_min` → `irregular`: manchas del fondo o piezas juntas en L). Se cuentan aparte en el inventario. `validez_solidez.png` justifica el umbral.

**Tipo.** LEGO se fabrica con un paso de 8 mm. El lado del rectángulo mínimo, dividido entre 8 mm, da la rejilla N×M, que es invariante a la rotación. Antes se resta el sesgo de borde medido (`correccion_borde_mm`). Si la rejilla no está cerca de un entero, la pieza sale como `dudoso` en vez de inventarse una clase.

**Color.** Se usa la mediana de S y V y la media circular de H sobre la pieza erosionada y sin brillos especulares. Si S es baja, la pieza es acromática (negro, gris o blanco según V). Si no, el tono H decide el color con cortes contiguos (`H < 7` → rojo, `H < 18` → naranja…), sin huecos entre tramos; el rojo aparece al principio y al final porque da la vuelta por 0.

**Inventario (Nivel 3).** Tabla tipo × color con totales por fila y columna, más las detecciones sin clasificar por motivo. Se ve en la imagen anotada y en la consola, y se guarda en `<escena>_inventario.json`.

## Limitaciones conocidas (para tratarlas en la memoria)

- Desde arriba **un brick y un plate del mismo N×M son indistinguibles** (solo cambia la altura). Elige tipos con siluetas distintas.
- Dos piezas **tocándose** se segmentan como una sola. Si forman una L, salen `irregular`. Pero **si quedan alineadas forman un rectángulo válido**: dos 1x2 lado con lado parecen un 2x2 y dos 2x2 parecen un 2x4, sin aviso. Habría que detectar la junta entre ellas (watershed o bordes internos).
- La homografía corrige el plano del tapete, no la **pared lateral** de las piezas altas, que se ve más cuanto más lejos del centro estén. Solo se reduce subiendo la cámara. Compruébalo con el mismo 2x4 en el centro y en las esquinas.
- **Piezas verdes** sobre fieltro verde: la segmentación se apoya en la diferencia de saturación y brillo. Hay que comprobarlo con datos antes de incluirlas.
- `num_studs` se calcula pero el árbol aún no lo usa. Es experimental y puede servir de verificación de la rejilla.
