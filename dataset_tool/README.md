# Extractor de frames — dataset de café

App local de una página: pega el link de un video (Facebook, YouTube, Instagram, TikTok — lo que sea que `yt-dlp` soporte) y saca fotos cada N segundos directo a `ml/dataset/raw/`, listas para subir a Roboflow y etiquetar.

## Uso

```bash
pip install yt-dlp flask certifi
python app.py
```

Abrir [http://localhost:5050](http://localhost:5050), pegar el link, elegir el intervalo (por defecto 1 frame cada 2 segundos) y enviar.

Los frames quedan en `../ml/dataset/raw/<nombre-del-video>_0001.jpg`, etc.

## Test

```bash
python test_app.py
```

Genera un video sintético con ffmpeg y valida que la extracción de frames dé el conteo esperado — no depende de internet.

## Notas

- Requiere `ffmpeg` en el PATH (ya lo tienes instalado).
- Los videos de Facebook deben ser públicos; si son privados, yt-dlp fallará con un error de acceso.
- El video descargado se borra después de extraer los frames — solo quedan las fotos.
