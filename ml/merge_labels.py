"""Pseudo-etiquetado: combina cajas HSV (auto_label) con detecciones del modelo ronda-1.

El HSV acierta el COLOR pero pierde granos en sombra/oscuros; el modelo ronda-1
aprendió la FORMA del grano y los recupera. Unión de ambos = mejor recall de etiquetas.
La clase de cada caja del modelo se reasigna por color dominante HSV dentro de la caja
(el modelo viejo solo conocía 3 clases; ahora son 4 con 'seco').

Uso: .venv/Scripts/python merge_labels.py   (reemplaza dataset/labeled/)
"""
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

import auto_label as al

HERE = Path(__file__).parent
MODEL = HERE / "runs" / "detect" / "train" / "weights" / "best.pt"
CONF = 0.20
IOU_DUP = 0.45      # solape a partir del cual dos cajas son el mismo grano
MIN_COLOR_FRAC = 0.05  # fracción mínima de píxeles de un color para aceptar caja del modelo


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua


def clase_por_color(hsv_img, box):
    """Clase dominante por color dentro de la caja; None si no hay color de grano."""
    x1, y1, x2, y2 = [max(0, int(v)) for v in box]
    crop = hsv_img[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    mejor, frac_mejor = None, MIN_COLOR_FRAC
    for idx, color in enumerate(al.CLASSES):
        mask = np.zeros(crop.shape[:2], dtype=np.uint8)
        for lo, hi in al.COLOR_RANGES[color]:
            mask |= cv2.inRange(crop, np.array(lo), np.array(hi))
        frac = (mask > 0).mean()
        if frac > frac_mejor:
            mejor, frac_mejor = idx, frac
    return mejor


def main():
    model = YOLO(str(MODEL))
    img_out = HERE / "dataset" / "labeled" / "images"
    lbl_out = HERE / "dataset" / "labeled" / "labels"
    import shutil
    shutil.rmtree(HERE / "dataset" / "labeled", ignore_errors=True)
    img_out.mkdir(parents=True)
    lbl_out.mkdir(parents=True)

    fotos = sorted((HERE / "dataset" / "raw").glob("*.jp*g"))
    tot = [0] * len(al.CLASSES)
    aportadas_modelo = 0
    for f in fotos:
        img, hsv_labels = al.procesar_imagen(f)
        if img is None:
            continue
        H, W = img.shape[:2]
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # cajas HSV en píxeles: (cls, x1,y1,x2,y2)
        cajas = [
            (cls, (cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H)
            for cls, cx, cy, w, h in hsv_labels
        ]

        # detecciones del modelo que no solapan con ninguna caja HSV
        res = model.predict(source=str(f), conf=CONF, verbose=False)[0]
        for b in res.boxes:
            box = b.xyxy[0].tolist()
            if any(iou(box, c[1:]) > IOU_DUP for c in cajas):
                continue
            cls = clase_por_color(hsv_img, box)
            if cls is None:
                continue  # sin color de grano adentro: probable falso positivo
            cajas.append((cls, *box))
            aportadas_modelo += 1

        shutil.copy2(f, img_out / f.name)
        with open(lbl_out / (f.stem + ".txt"), "w") as fh:
            for cls, x1, y1, x2, y2 in cajas:
                tot[cls] += 1
                cx, cy = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H
                w, h = (x2 - x1) / W, (y2 - y1) / H
                fh.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    print(f"fotos: {len(fotos)} | cajas aportadas por el modelo: {aportadas_modelo}")
    print("instancias:", ", ".join(f"{c}={n}" for c, n in zip(al.CLASSES, tot)))


if __name__ == "__main__":
    main()
