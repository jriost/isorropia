# Isorropia ML — Detección de granos de café

3 clases: `verde` (no cosechar), `naranja`/pintón (no cosechar), `rojo` (**el único que se cosecha**).

Pipeline actual (bootstrap por color, sin etiquetado manual):

```
dataset/raw/*.jpg → auto_label.py → dataset/labeled/ → prepare_split.py → dataset/split/
                                                                              │
                                                                         train.py
                                                                              │
                                                              runs/detect/train/weights/best.pt
```

Entorno: `ml/.venv` (Python 3.12 de python.org — **no** el de MSYS2, los wheels de PyTorch no calzan con ese ABI).

## 1. Auto-etiquetar por color

Las 3 clases son literalmente colores, así que en vez de dibujar cajas a mano se detectan
por umbral HSV + filtro de forma (circularidad, para no confundir hojas verdes con granos verdes).

```bash
.venv/Scripts/python auto_label.py --debug 8   # --debug guarda N previews con cajas dibujadas
```

**Techo conocido de este método** (ver comentario `ponytail:` en el código):
- Racimos muy apretados se fusionan y quedan sin caja individual (se descartan, no se
  inventan cajas malas) → sub-cuenta en zonas de cosecha densa.
- Corteza/tierra bajo sombra puede colar algún falso positivo `verde`.
- **Si la precisión no alcanza:** revisar/corregir `dataset/labeled/labels/*.txt` a mano
  (formato YOLO estándar) o subir `dataset/raw/` a Roboflow y etiquetar ahí.

## 2. Dividir en train/val

```bash
.venv/Scripts/python prepare_split.py --val-frac 0.15
```

Genera `dataset/split/{train,val}/{images,labels}` + `data.yaml`.

## 3. Entrenar

```bash
.venv/Scripts/python train.py
```

Salida: `runs/detect/train/weights/best.pt`. Métrica objetivo: **mAP50 > 0.85 en `rojo`**
(es la única clase que importa para la cosecha — `verde`/`naranja` solo hay que reconocerlos
para NO tocarlos).

## 4. Exportar

```bash
.venv/Scripts/yolo export model=runs/detect/train/weights/best.pt format=tfjs   # app web
.venv/Scripts/yolo export model=runs/detect/train/weights/best.pt format=onnx   # robot
```

Copiar la carpeta TF.js exportada a `app_camara/model/` y actualizar el `loadModel()` en
`app_camara/index.html` (hoy usa un placeholder COCO-SSD — está marcado con `// ponytail:`).

## 5. Probar detección con coordenadas

```bash
.venv/Scripts/python detect.py --source foto.jpg --model runs/detect/train/weights/best.pt
```

Imprime el JSON del contrato con el brazo (Fase 3):

```json
{"detecciones": [{"clase": "rojo", "conf": 0.91, "cx": 0.62, "cy": 0.41, "w": 0.05, "h": 0.06}]}
```

> `cx, cy` son el centro de la caja normalizado (0-1). La `z` (distancia) la agrega el
> hardware de profundidad en Fase 2 semana 5 (OAK-D o ToF).

## Cuando haya más fotos / se quiera mejorar precisión

Repetir desde el paso 1 con más fotos en `dataset/raw/`, o reemplazar el auto-etiquetado
por etiquetado manual en Roboflow si el auto-label no alcanza la precisión necesaria
para que el gripper no falle (el brazo necesita cajas ajustadas, no solo "hay un grano ahí").
