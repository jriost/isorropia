"""Self-check de extraer_frames() sin depender de red: genera un video
sintético de 6s con ffmpeg y valida que el conteo de frames sea el esperado.
Uso: python test_app.py
"""
import shutil
import subprocess
from pathlib import Path

from app import OUTPUT_DIR, TMP_DIR, extraer_frames


def test_extraer_frames():
    video = TMP_DIR / "synthetic_test.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=6", video.as_posix()],
        check=True, capture_output=True,
    )
    try:
        n = extraer_frames(video, intervalo=2)  # 6s / 2s ≈ 3 frames
        assert n == 3, f"esperaba 3 frames, salieron {n}"
        print(f"OK — {n} frames extraídos correctamente")
    finally:
        video.unlink(missing_ok=True)
        for f in OUTPUT_DIR.glob("synthetic_test_*.jpg"):
            f.unlink()


if __name__ == "__main__":
    test_extraer_frames()
