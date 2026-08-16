r"""Entrenamiento automático disparado desde la página.

La página deja un flag en el servidor (PUT entrenar.flag). Este script corre cada
15 min por tarea programada de Windows: si hay flag, baja las fotos nuevas de las
carpetas del servidor, reentrena, exporta ONNX y sube el modelo nuevo a la página.

Instalación de la tarea (una vez, en cmd como el usuario):
  schtasks /create /sc minute /mo 15 /tn IsorropiaEntrenar /tr "\"%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe\" \"C:\Users\Usuario\Documents\Proyectos\cielo\isorropia\ml\entrenar_auto.py\""

ponytail: lockfile simple contra corridas concurrentes; si el PC se apaga a mitad
de entrenamiento, el lock queda huérfano y se ignora tras 12 h.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
BASE_URL = "https://isorropia.fincaelcielocoffee.com"
UP = f"{BASE_URL}/subir-ds-x7k9"
CARPETAS = ["rojos", "verdes", "rojo_verdes", "naranjas", "secos"]
RAW = HERE / "dataset" / "raw"
LOCK = HERE / ".train.lock"
LOG = HERE / "entrenar_auto.log"
PY = HERE / ".venv" / "Scripts" / "python.exe"
SSH_KEY = HERE.parent / ".server_key"
SERVER = "root@198.96.88.153"


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def http(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method, data=data)
    return urllib.request.urlopen(req, timeout=30)


def hay_flag():
    try:
        http(f"{UP}/entrenar.flag")
        return True
    except Exception:
        return False


def bajar_fotos_nuevas():
    existentes = {p.name for p in RAW.glob("*.jp*g")}
    hashes = {hashlib.md5(p.read_bytes()).hexdigest() for p in RAW.glob("*.jp*g")}
    nuevas = 0
    for carpeta in CARPETAS:
        try:
            lista = json.loads(http(f"{UP}/{carpeta}/").read())
        except Exception:
            continue
        for item in lista:
            if item.get("type") != "file" or not item["name"].lower().endswith(".jpg"):
                continue
            dest_name = f"{carpeta}_{item['name']}"
            if dest_name in existentes:
                continue
            datos = http(f"{UP}/{carpeta}/{item['name']}").read()
            if hashlib.md5(datos).hexdigest() in hashes:
                continue
            (RAW / dest_name).write_bytes(datos)
            nuevas += 1
    return nuevas


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, cwd=str(HERE), **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{args[:2]}... fallo:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def ultimo_run():
    runs = sorted((HERE / "runs" / "detect").glob("train*"), key=lambda p: p.stat().st_mtime)
    return runs[-1]


def main():
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 12 * 3600:
        return  # otra corrida en curso
    if not hay_flag():
        return
    if not SSH_KEY.exists():
        log("ERROR: falta .server_key — extraerla de cielo.ssh"); return

    LOCK.write_text(str(os.getpid()))
    try:
        log("flag detectado — iniciando")
        n = bajar_fotos_nuevas()
        log(f"fotos nuevas bajadas: {n}")

        run([str(PY), "auto_label.py"])
        run([str(PY), "prepare_split.py"])
        log("etiquetado y split listos — entrenando (esto toma horas)")
        run([str(PY), "train.py"], timeout=12 * 3600)

        pesos = ultimo_run() / "weights"
        run([str(PY), "-c",
             f"from ultralytics import YOLO; YOLO(r'{pesos / 'best.pt'}').export(format='onnx', imgsz=640, simplify=True)"])
        metricas = json.loads((pesos / "metrics.json").read_text(encoding="utf-8"))

        info = {
            "fecha": f"{datetime.now():%Y-%m-%d %H:%M}",
            "fotos": len(list(RAW.glob("*.jp*g"))),
            "map50": metricas["map50"],
            "map50_rojo": metricas["por_clase"].get("rojo"),
            "por_clase": metricas["por_clase"],
        }
        info_path = pesos / "info.json"
        info_path.write_text(json.dumps(info), encoding="utf-8")

        ssh_opts = ["-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no"]
        run(["scp", *ssh_opts, str(pesos / "best.onnx"), f"{SERVER}:/var/www/isorropia_camara/model/best.onnx"])
        run(["scp", *ssh_opts, str(info_path), f"{SERVER}:/var/www/isorropia_camara/model/info.json"])
        http(f"{UP}/entrenar.flag", method="DELETE")
        log(f"modelo desplegado ✓ mAP50={metricas['map50']} rojo={info['map50_rojo']}")
    except Exception as e:
        log(f"ERROR: {e}")
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
