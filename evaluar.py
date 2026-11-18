"""
Evaluación cuantitativa: compara el inventario del programa con el real (anotado a mano).
Uso: python evaluar.py
"""
import contextlib
import io
from collections import Counter
import lego

ESCENA_A = Counter({"1x6 blanco": 1, "2x2 blanco": 1, "2x2 gris": 1, "2x2 marron": 3, "2x4 gris": 2,
                    "2x4 marron": 2, "2x6 gris": 1, "4x4 azul": 1, "6x6 blanco": 1})
ESCENA_B = Counter({"1x1 negro": 1, "1x2 amarillo": 1, "1x2 marron": 1, "1x2 rojo": 1, "1x4 azul": 1,
                    "2x2 azul": 1, "2x2 beige": 1, "2x2 marron": 2, "2x4 beige": 2, "2x4 gris": 1,
                    "2x4 marron": 2, "4x4 azul": 1, "8x8 beige": 1})
ESCENA_C = Counter({"1x1 negro": 1, "1x2 amarillo": 1, "1x2 rojo": 1, "1x4 azul": 1, "2x2 azul": 1,
                    "2x4 beige": 2, "2x4 gris": 1, "2x4 marron": 1, "4x4 azul": 1, "8x8 beige": 1})
ESCENA_D = ESCENA_C - Counter({"2x4 beige": 1, "2x4 marron": 1})
ESCENA_E = Counter({"1x2 rosa": 1, "1x2 azul": 1, "2x2 azul": 1, "1x2 rojo": 1, "1x1 negro": 1})

# Verdad de referencia por foto (IMG_4178 se excluye: tomada a otra altura)
REAL = {4173: ESCENA_A, 4174: ESCENA_A, 4175: ESCENA_A, 4176: ESCENA_A, 4177: ESCENA_A,
        4179: ESCENA_B, 4180: ESCENA_B, 4181: ESCENA_C, 4182: ESCENA_C, 4183: ESCENA_D,
        4184: ESCENA_E, 4185: Counter({"1x1 negro": 1}), 4186: Counter({"2x2 azul": 1})}

total_real = total_ok = total_falsos = 0
print(f"{'foto':<10}{'reales':>7}{'aciertos':>9}{'fallos':>7}{'sobran':>7}")
for n, real in REAL.items():
    with contextlib.redirect_stdout(io.StringIO()):           # silencia la salida de lego.py
        pred = lego.analizar(f"fotos/IMG_{n}.jpg", devolver_inventario=True)
    ok = sum((real & pred).values())                          # piezas bien detectadas y clasificadas
    nr, falsos = sum(real.values()), sum((pred - real).values())
    total_real, total_ok, total_falsos = total_real + nr, total_ok + ok, total_falsos + falsos
    print(f"IMG_{n:<6}{nr:>7}{ok:>9}{nr - ok:>7}{falsos:>7}   {dict(pred - real) or ''}")

print(f"\nTOTAL: {total_ok}/{total_real} aciertos = {100 * total_ok / total_real:.1f} %"
      f"   (detecciones sobrantes o mal clasificadas: {total_falsos})")
