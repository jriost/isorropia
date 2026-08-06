"""Detecta granos de café y emite el JSON del contrato con el brazo.

Uso:
    python detect.py --source foto.jpg
    python detect.py --source 0            # webcam
    python detect.py --source foto.jpg --model runs/detect/train/weights/best.pt
"""
import argparse
import json

from ultralytics import YOLO


def detecciones_json(result):
    """Convierte un resultado YOLO al contrato JSON (coords normalizadas 0-1)."""
    dets = []
    for box in result.boxes:
        cx, cy, w, h = box.xywhn[0].tolist()
        dets.append({
            "clase": result.names[int(box.cls)],
            "conf": round(float(box.conf), 2),
            "cx": round(cx, 3),
            "cy": round(cy, 3),
            "w": round(w, 3),
            "h": round(h, 3),
            # "z": la agrega el sensor de profundidad en Fase 2 sem 5
        })
    return {"detecciones": dets}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="imagen, carpeta o 0 para webcam")
    ap.add_argument("--model", default="runs/detect/train/weights/best.pt")
    ap.add_argument("--conf", type=float, default=0.5)
    args = ap.parse_args()

    model = YOLO(args.model)
    source = int(args.source) if args.source.isdigit() else args.source

    for result in model.predict(source=source, conf=args.conf, stream=True, show=True):
        print(json.dumps(detecciones_json(result), ensure_ascii=False))


if __name__ == "__main__":
    main()


def test_contrato():
    # ponytail: smoke test del formato sin modelo — valida solo la estructura
    class _Box:
        cls = 0
        conf = 0.9
        class _T(list):
            def tolist(self):
                return list(self)
        xywhn = [_T([0.5, 0.5, 0.1, 0.1])]

    class _R:
        names = {0: "maduro"}
        boxes = [_Box()]

    out = detecciones_json(_R())
    assert out["detecciones"][0]["clase"] == "maduro"
    assert 0 <= out["detecciones"][0]["cx"] <= 1
