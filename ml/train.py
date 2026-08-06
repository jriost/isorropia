"""Entrena YOLO11n para detectar granos de café: verde, naranja, rojo.

Requiere dataset/split/data.yaml (generar con: python auto_label.py && python prepare_split.py,
o con un dataset etiquetado a mano en Roboflow con el mismo formato).
"""
from ultralytics import YOLO


def main():
    model = YOLO("yolo11n.pt")  # nano: corre en celular y Raspberry Pi
    model.train(
        data="dataset/split/data.yaml",
        epochs=80,
        imgsz=640,
        batch=8,        # dataset chico + CPU-only; subir si hay GPU
        patience=20,    # early stopping
    )
    metrics = model.val()
    print(f"\nmAP50: {metrics.box.map50:.3f}  (objetivo: >0.85)")
    for i, cls in model.names.items():
        print(f"  {cls}: mAP50={metrics.box.ap50[i]:.3f}")
    print("Pesos: runs/detect/train/weights/best.pt")


if __name__ == "__main__":
    main()
