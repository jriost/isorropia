"""App local: pega un link de video (Facebook/YouTube/Instagram/TikTok...) y
extrae frames a una carpeta para armar el dataset de granos de café.

Uso:
    pip install yt-dlp flask   # ffmpeg debe estar instalado y en el PATH
    python app.py
    abrir http://localhost:5050

ponytail: descarga y extracción síncronas (la request espera a que termine).
Para videos largos se siente lento pero funciona. Si estorba, pasar a un
job en background con progreso — no antes de necesitarlo.
"""
import os
import subprocess
import uuid
from pathlib import Path

import certifi

# ponytail: algunos Python de Windows (MSYS2/mingw) no traen CA raíz configurada
# → yt-dlp falla verificando HTTPS. Apuntamos al bundle de certifi antes de importar yt_dlp.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import yt_dlp
from flask import Flask, render_template_string, request

BASE = Path(__file__).parent
OUTPUT_DIR = BASE.parent / "ml" / "dataset" / "raw"
TMP_DIR = BASE / "_tmp_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

PAGE = """
<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Isorropia — Extractor de frames</title>
<style>
  body { font-family: system-ui, sans-serif; background: #14100c; color: #f0e6d8; max-width: 560px; margin: 60px auto; padding: 0 20px; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  p.sub { color: #a89880; font-size: 12px; margin-bottom: 28px; }
  label { font-size: 12px; color: #a89880; display: block; margin-bottom: 4px; }
  input[type=text], input[type=number] { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #35291d; background: #1f1812; color: #fff; margin-bottom: 16px; }
  button { width: 100%; padding: 12px; border: none; border-radius: 10px; background: #6F4E37; color: #fff; font-weight: 700; cursor: pointer; }
  .msg { margin-top: 20px; padding: 14px; border-radius: 10px; font-size: 13px; }
  .ok { background: #16321f; border: 1px solid #2a5c39; }
  .err { background: #3a1616; border: 1px solid #6b2626; }
  .folder { font-family: monospace; font-size: 11px; color: #a89880; word-break: break-all; }
</style></head><body>
  <h1>☕ Extractor de frames — Isorropia</h1>
  <p class="sub">Pega el link de un video (Facebook, YouTube, Instagram, TikTok...) y saca fotos para el dataset de café.</p>
  <form method="post">
    <label>URL del video</label>
    <input type="text" name="url" placeholder="https://www.facebook.com/..." required value="{{ url or '' }}">
    <label>Un frame cada N segundos</label>
    <input type="number" name="intervalo" value="{{ intervalo or 2 }}" min="1" step="0.5">
    <button type="submit">Descargar y extraer frames</button>
  </form>
  {% if mensaje %}
    <div class="msg {{ 'ok' if ok else 'err' }}">
      {{ mensaje }}
      {% if carpeta %}<div class="folder">{{ carpeta }}</div>{% endif %}
    </div>
  {% endif %}
</body></html>
"""


def descargar_video(url: str) -> Path:
    """Descarga el video con yt-dlp y devuelve la ruta del archivo."""
    nombre = str(uuid.uuid4())
    destino = TMP_DIR / f"{nombre}.%(ext)s"
    opts = {
        "outtmpl": str(destino),
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    archivos = list(TMP_DIR.glob(f"{nombre}.*"))
    if not archivos:
        raise RuntimeError("yt-dlp no generó ningún archivo de video.")
    return archivos[0]


def extraer_frames(video_path: Path, intervalo: float) -> int:
    """Extrae un frame cada `intervalo` segundos con ffmpeg. Devuelve cuántos se crearon."""
    prefijo = video_path.stem
    patron = str(OUTPUT_DIR / f"{prefijo}_%04d.jpg")
    fps = 1 / intervalo
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vf", f"fps={fps}", "-qscale:v", "2", patron],
        check=True, capture_output=True,
    )
    return len(list(OUTPUT_DIR.glob(f"{prefijo}_*.jpg")))


@app.route("/", methods=["GET", "POST"])
def index():
    ctx = {}
    if request.method == "POST":
        url = request.form["url"].strip()
        intervalo = float(request.form.get("intervalo") or 2)
        ctx.update(url=url, intervalo=intervalo)
        video_path = None
        try:
            video_path = descargar_video(url)
            n = extraer_frames(video_path, intervalo)
            ctx["ok"] = True
            ctx["mensaje"] = f"✓ {n} frames guardados en el dataset."
            ctx["carpeta"] = str(OUTPUT_DIR)
        except Exception as e:
            ctx["ok"] = False
            ctx["mensaje"] = f"Error: {e}"
        finally:
            if video_path and video_path.exists():
                video_path.unlink()
    return render_template_string(PAGE, **ctx)


if __name__ == "__main__":
    app.run(port=5050, debug=True)
