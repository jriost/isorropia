"""Divide dataset/labeled/ en train/val y escribe data.yaml para YOLO.

Uso: python prepare_split.py [--val-frac 0.15]
"""
import argparse
import random
import shutil
from pathlib import Path

HERE = Path(__file__).parent
LABELED = HERE / "dataset" / "labeled"
SPLIT = HERE / "dataset" / "split"
CLASSES = ["verde", "naranja", "rojo"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-frac", type=float, default=0.15)
    args = ap.parse_args()

    imgs = sorted((LABELED / "images").glob("*.*"))
    random.Random(42).shuffle(imgs)  # semilla fija: split reproducible
    n_val = max(1, int(len(imgs) * args.val_frac))
    splits = {"val": imgs[:n_val], "train": imgs[n_val:]}

    if SPLIT.exists():
        shutil.rmtree(SPLIT)

    for split, files in splits.items():
        (SPLIT / split / "images").mkdir(parents=True, exist_ok=True)
        (SPLIT / split / "labels").mkdir(parents=True, exist_ok=True)
        for img in files:
            lbl = LABELED / "labels" / (img.stem + ".txt")
            shutil.copy2(img, SPLIT / split / "images" / img.name)
            if lbl.exists():
                shutil.copy2(lbl, SPLIT / split / "labels" / lbl.name)

    yaml_text = (
        f"path: {SPLIT.resolve()}\n"
        f"train: train/images\n"
        f"val: val/images\n"
        f"nc: {len(CLASSES)}\n"
        f"names: {CLASSES}\n"
    )
    (SPLIT / "data.yaml").write_text(yaml_text, encoding="utf-8")

    print(f"train={len(splits['train'])} val={len(splits['val'])}")
    print(f"data.yaml -> {SPLIT / 'data.yaml'}")


if __name__ == "__main__":
    main()
