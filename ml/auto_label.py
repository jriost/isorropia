"""Auto-etiquetador por color para granos de café: verde, naranja, rojo.

Las 3 clases del proyecto SON colores, así que en vez de dibujar cajas a mano
foto por foto, se detectan por umbral HSV + filtro de forma (los granos son
blobs redondos; las hojas y ramas no lo son, aunque compartan tono verde).

ponytail: esto es un bootstrap por color clásico (OpenCV), no un modelo.
Techo conocido: racimos muy apretados se fusionan en una sola caja, y hojas
verdes brillantes bajo luz directa pueden colarse como falsos "verde".
Camino de mejora: revisar/corregir cajas en Roboflow antes de reentrenar.

Uso:
    python auto_label.py                # procesa dataset/raw/ → dataset/labeled/
    python auto_label.py --debug 8       # además guarda 8 previews con cajas dibujadas
"""
import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
RAW_DIR = HERE / "dataset" / "raw"
OUT_DIR = HERE / "dataset" / "labeled"
CLASSES = ["verde", "naranja", "rojo", "seco"]  # índices 0-3 — deben calzar con data.yaml

# Rangos HSV (OpenCV: H 0-180, S/V 0-255). El rojo maduro va de rojo brillante
# a vinotinto oscuro (variedad Caturra/Bourbon), por eso el rango es amplio en V.
# "seco" (podrido/marrón) = tono naranja-café oscuro; se separa de "naranja" por V:
# naranja brillante V>=110, seco oscuro V<110. Las ramas también son marrones,
# pero el filtro de circularidad las descarta (son alargadas, no redondas).
COLOR_RANGES = {
    "verde":   [((35, 60, 40), (85, 255, 255))],
    "naranja": [((10, 100, 110), (32, 255, 255))],  # incluye amarillo: variedad amarilla y pintón claro
    "rojo":    [((0, 60, 30), (9, 255, 255)), ((165, 60, 30), (180, 255, 255))],
    "seco":    [((5, 40, 30), (25, 255, 109))],
}

MIN_AREA_FRAC = 0.0003    # área mínima de un grano; también filtra manchas amarillas de hojas
MAX_AREA_FRAC = 0.15      # granos en primer plano (distancia de trabajo del brazo) son grandes
MIN_CIRCULARITY = 0.5     # 1.0 = círculo perfecto; hojas/ramas quedan muy por debajo


def mask_for(hsv, color):
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in COLOR_RANGES[color]:
        mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def boxes_from_mask(mask, img_area):
    boxes = []
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        area = cv2.contourArea(c)
        frac = area / img_area
        if frac < MIN_AREA_FRAC or frac > MAX_AREA_FRAC:
            continue
        perim = cv2.arcLength(c, True)
        if perim == 0:
            continue
        circularity = 4 * np.pi * area / (perim * perim)
        if circularity < MIN_CIRCULARITY:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if not (0.5 <= w / h <= 2.0):  # los granos son ~redondos, no alargados
            continue
        boxes.append((x, y, w, h))
    return boxes


def procesar_imagen(path):
    img = cv2.imread(str(path))
    if img is None:
        return None, []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, W = img.shape[:2]
    area = H * W

    labels = []
    for cls_idx, color in enumerate(CLASSES):
        mask = mask_for(hsv, color)
        for (x, y, w, h) in boxes_from_mask(mask, area):
            cx, cy = (x + w / 2) / W, (y + h / 2) / H
            labels.append((cls_idx, cx, cy, w / W, h / H))
    return img, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", type=int, default=0, help="guardar N previews con cajas dibujadas")
    args = ap.parse_args()

    # limpiar salidas previas: si una foto se renombra/borra entre corridas,
    # una salida vieja sin limpiar deja huérfanos que inflan el conteo silenciosamente
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    img_out = OUT_DIR / "images"
    lbl_out = OUT_DIR / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    fotos = sorted(RAW_DIR.glob("*.jp*g")) + sorted(RAW_DIR.glob("*.png"))
    if not fotos:
        print(f"No hay fotos en {RAW_DIR}")
        return

    debug_dir = HERE / "dataset" / "debug_preview"
    debug_sample = set(random.sample(fotos, min(args.debug, len(fotos)))) if args.debug else set()
    if debug_sample:
        debug_dir.mkdir(parents=True, exist_ok=True)

    total_labels = [0] * len(CLASSES)
    vacias = 0
    for foto in fotos:
        img, labels = procesar_imagen(foto)
        if img is None:
            continue
        if not labels:
            vacias += 1

        dest_img = img_out / foto.name
        cv2.imwrite(str(dest_img), img)
        dest_lbl = lbl_out / (foto.stem + ".txt")
        with open(dest_lbl, "w") as f:
            for cls_idx, cx, cy, w, h in labels:
                total_labels[cls_idx] += 1
                f.write(f"{cls_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        if foto in debug_sample:
            vis = img.copy()
            H, W = img.shape[:2]
            colors_bgr = {0: (0, 200, 0), 1: (0, 140, 255), 2: (0, 0, 220), 3: (40, 70, 120)}
            for cls_idx, cx, cy, w, h in labels:
                x1, y1 = int((cx - w / 2) * W), int((cy - h / 2) * H)
                x2, y2 = int((cx + w / 2) * W), int((cy + h / 2) * H)
                cv2.rectangle(vis, (x1, y1), (x2, y2), colors_bgr[cls_idx], 3)
            cv2.imwrite(str(debug_dir / foto.name), vis)

    print(f"Procesadas {len(fotos)} fotos -> {img_out}")
    print(f"Instancias por clase: " + ", ".join(f"{c}={n}" for c, n in zip(CLASSES, total_labels)))
    print(f"Fotos sin ninguna deteccion: {vacias}")
    if debug_sample:
        print(f"Previews de revision en: {debug_dir}")


if __name__ == "__main__":
    main()
