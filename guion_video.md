# Guion del vídeo: Reto 07 LEGO

**Duración aproximada:** 8 minutos.

**Cómo grabar:** graba **un audio por bloque** (7 archivos) y ponles el nombre del bloque:
`01_intro`, `02_montaje`, `03_funcionamiento`, `04_prueba1`, `05_prueba2`, `06_resultados` y `07_cierre`.

- Habla tranquilo, sin prisa. Si te equivocas, vuelve a grabar **el bloque entero**.
- Deja un segundo de silencio al principio y al final de cada audio.
- Lo que va entre [corchetes] es para que lo adaptes a lo que sale en tus vídeos de prueba.

---

## 01_intro (unos 30 s)
*En pantalla: título del proyecto y una foto de las piezas en el tapete.*

> Hola, soy Héctor Ares, y este es mi proyecto para el parcial de Inteligencia Artificial. Mi reto es el de LEGO: he hecho un programa que, a partir de una foto del tapete hecha desde arriba, encuentra todas las piezas, dice de qué tamaño y de qué color es cada una, y al final hace un inventario. Y todo sin redes neuronales ni nada entrenado: solo procesamiento de imagen y reglas que he sacado midiendo mis propias fotos.

## 02_montaje (unos 45 s)
*En pantalla: el montaje (sale en tus vídeos) y la vista de la cámara.*

> El montaje es bastante casero. Tengo un tapete de fieltro verde de 40 por 60 centímetros dentro de una caja, el móvil fijo encima a unos 40 centímetros y como luz uso la linterna del móvil.
>
> Lo más importante es que el móvil esté siempre a la misma altura. Así sé que cada milímetro son 8 píxeles en la foto, y puedo medir las piezas de verdad. Para que os hagáis una idea, la pieza más pequeña, la uno por uno, ocupa unos 60 píxeles, así que se ve de sobra.
>
> El proceso es: hago la foto, la paso al ordenador y la abro con el programa.

## 03_funcionamiento (unos 2 min)
*En pantalla: diagrama del proceso, segmentación paso a paso, árbol de decisión y gráfica de colores.*

> El programa hace cuatro cosas.
>
> Primero, **separa las piezas del fondo**. Como el tapete es verde y ninguna pieza lo es, todo lo que no es verde es una pieza. Luego limpio un poco la imagen para quitar puntitos sueltos y rellenar huecos, y me quedo con el contorno de cada pieza. También descarto cosas que no son piezas, como trozos del cartón del borde.
>
> Segundo, **mide cada pieza**. Le ajusto un rectángulo, aunque esté girada, y saco el ancho y el largo en milímetros. Como cada tetón de LEGO mide 8 milímetros, con eso sé si es una dos por dos, una dos por cuatro o la que sea.
>
> Tercero, **mira el color**. Calculo el color de la pieza quitando los brillos de la linterna, que si no la confunden, y lo paso por una serie de preguntas: ¿tira a azul?, ¿tira a rojo?, ¿es oscura?, ¿es clara?... Así hasta llegar a uno de los nueve colores que tengo.
>
> Y cuarto, **junta las dos cosas**: tamaño más color me da la pieza, por ejemplo "dos por cuatro marrón", y al final cuenta cuántas hay de cada.
>
> Todo esto es el árbol de decisión. Lo importante es que ningún límite está puesto a ojo: medí las 135 piezas de mis fotos y puse cada corte justo a mitad de camino entre dos colores o dos tamaños. En esta gráfica se ve cómo cada color queda en su zona.

## 04_prueba1 (lo que dure tu primer vídeo, unos 1:30)
*En pantalla: tu primer vídeo de prueba.*

> Vamos con la primera prueba. He puesto [número] piezas en el tapete, mezclando tamaños y colores, y en posiciones y giros distintos.
>
> Hago la foto, la paso al ordenador y la abro con el programa.
>
> Aquí está el resultado: cada pieza sale recuadrada con su tipo y su color. Si lo comparamos con lo que hay en el tapete, [ha acertado todas / comentar lo que pase]. Por ejemplo, [la pieza X], que está [girada / con brillo / en la esquina], también la reconoce bien.
>
> Y abajo tenemos el inventario: [leer dos o tres líneas, por ejemplo "tres dos por dos marrones, dos dos por cuatro beige..."].

## 05_prueba2 (lo que dure tu segundo vídeo, unos 1:30)
*En pantalla: tu segundo vídeo de prueba.*

> En la segunda prueba cambio las piezas: [quito unas, pongo otras / las muevo y las giro].
>
> Quería probar también los casos más difíciles: [la pieza azul con el reflejo de la linterna / blanco, gris y beige juntas, que son muy parecidas / la uno por uno negra].
>
> El resultado: [ha acertado todas]. Fijaos en [la pieza difícil]: aunque [le da el brillo / el color se parece mucho a otra], el programa la clasifica bien. Y el inventario se actualiza solo con los cambios que he hecho.

## 06_resultados (unos 45 s)
*En pantalla: tabla de resultados.*

> Para medir lo bien que funciona, apunté a mano lo que había en cada foto y lo comparé con lo que dice el programa.
>
> En las 13 fotos que usé para hacerlo acertó las 135 piezas. Pero claro, con esas fotos ajusté los límites, así que es normal que acierte. Lo que de verdad cuenta es lo que pasa con fotos nuevas, y en 3 pruebas nuevas, sin tocar nada del programa, acertó las 18 piezas. Y en las pruebas que acabáis de ver, [tampoco ha fallado].

## 07_cierre (unos 40 s)
*En pantalla: limitaciones y despedida.*

> Eso sí, tiene sus limitaciones. El móvil tiene que estar siempre a la misma altura, las piezas no pueden estar tocándose, y una pieza verde no se vería sobre el tapete verde. Además, la luz influye bastante, sobre todo en las piezas negras y en las que brillan.
>
> Aun así, creo que demuestra que con visión clásica y reglas bien medidas se puede hacer un sistema que reconoce y cuenta piezas LEGO de forma fiable. El código está en mi GitHub, que está enlazado en el trabajo. Muchas gracias.

---

## Qué me tienes que pasar
1. **Los 7 audios** (vale cualquier formato: m4a de notas de voz, mp3, wav...).
2. **Los 2 vídeos de las pruebas.**
3. Si en los vídeos sale el montaje, dímelo, y si no, **unos segundos grabando el montaje** con otro móvil.
