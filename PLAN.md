# Isorropia — Plan de Trabajo

**Proyecto:** Robot recolector de café · Finca El Cielo
**Estado al 27 de julio de 2026:** componentes comprados (✅ ~13 jul) · impresión 3D en curso desde el 20 jul · fotos de granos en recopilación ✅
**Activos actuales:** Brazo robótico (STEP + STL), APK `isorropia_harvest`, logo, app cámara prototipo, scaffold ML

---

## Resumen de fases

| Fase | Qué | Duración | Fechas | Estado |
|------|-----|----------|--------|--------|
| 0 | Setup: BOM, compra de componentes | ✅ | ~13 jul | Hecho (falta repo GitHub) |
| 1 | Robot recolector: mecánica + impresión 3D | 4 sem | 20 jul – 16 ago | 🔄 En curso (sem 2 de impresión) |
| 2 | Modelo ML + app de detección de café (distancia y coordenadas) | 5 sem | 3 ago – 6 sep | 🔄 Dataset en recopilación |
| 3 | Integración Fase 1 + Fase 2 | 4 sem | 7 sep – 4 oct | — |
| 4 | Sistema de cable (~1 m) para mover brazo árbol a árbol | 5 sem | 5 oct – 8 nov | — |
| — | Pruebas de campo en la finca + iteración | 3 sem | 9 – 29 nov | — |

> Fase 2 corre en paralelo con la segunda mitad de Fase 1: mientras las piezas se imprimen, se etiqueta el dataset y se entrena el modelo.

---

## Fase 0 — Setup ✅ (~13 jul)

- [x] BOM y compra de componentes
- [ ] Crear repo GitHub `isorropia` (subir STEP, STL, APK, este plan) — **único pendiente**

### BOM inicial

| Componente | Uso | Cant. | Nota |
|------------|-----|-------|------|
| Servos MG996R | Articulaciones del brazo | 4-6 | Metal gear |
| ESP32 | Controlador del brazo | 2 | Uno de repuesto |
| Fuente 5-6V 5A | Alimentar servos | 1 | Los servos pican corriente |
| PLA/PETG 1kg | Impresión de piezas | 2 | PETG para piezas de carga |
| Rodamientos 608ZZ | Waist + poleas trole | 8 | Los mismos sirven para Fase 4 |
| Cámara OAK-D Lite (o ESP32-CAM + ToF VL53L0X) | Visión + profundidad | 1 | Ver Fase 2 |
| Tornillería M3/M4 | Ensamble | kit | — |

**Entregable:** repo creado + componentes pedidos

---

## Fase 1 — Mecánica e impresión 3D (20 jul – 16 ago) 🔄

**Semana 1-2 (20 jul – 2 ago):** impresión de piezas — 🔄 en curso
- [ ] Imprimir Base, Waist, Arm 01/02/03, engranajes (gear1, gear2)
- [ ] Imprimir Gripper (base + links) — pieza crítica, puede necesitar reimpresión con ajustes

**Semana 3 (3–9 ago):** ensamble
- [ ] Ensamble mecánico completo con servos
- [ ] Cableado al ESP32

**Semana 4 (10–16 ago):** movimiento
- [ ] Firmware básico: mover cada articulación por serial/WiFi
- [ ] Cinemática inversa: llevar el gripper a una coordenada (x, y, z) dada
- [ ] Prueba: agarrar un grano/objeto pequeño en posición conocida

**Entregable:** brazo que agarra un objeto en coordenadas dictadas manualmente

---

## Fase 2 — Modelo ML + App de detección (3 ago – 6 sep)

### Arquitectura

```
[Fotos de campo] → [Etiquetado] → [Entrenamiento YOLO] → exporta 2 destinos:
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                     ▼
              [App Android (TFLite)]              [Módulo robot (Python)]
              demo + validación en campo          detección + (x,y,z) → brazo
```

### Semana 1-2 (3–16 ago): dataset

Ya se están recopilando fotos ✅. Especificación para que sirvan:

- **Clases:** `maduro` (rojo), `pinton`, `verde`, `seco` — 4 clases
- **Cantidad mínima:** 500 fotos (ideal 1.000+), con varios granos por foto
- **Variedad:** luz de mañana/tarde/nublado · con y sin sombra · distancias 20-60 cm (la distancia de trabajo del brazo) · granos ocultos parcialmente por hojas
- **Formato:** la resolución nativa del celular está bien; no recortar ni editar
- [ ] Subir a Roboflow (gratis) y etiquetar con cajas (bounding boxes)
- [ ] Split 80/10/10 train/valid/test

### Semana 3-4 (17–30 ago): modelo

- [ ] Entrenar YOLO11n (nano) en Colab/local — corre en celular y en Raspberry Pi
- [ ] Métrica objetivo: **mAP50 > 0.85 en clase `maduro`** (la única que se cosecha)
- [ ] Exportar a **TFLite** (para la app Android) y **ONNX** (para el módulo del robot)
- [ ] Si el mAP no da: revisar etiquetas, aumentar dataset, subir a YOLO11s

### Semana 5 (31 ago – 6 sep): distancia y coordenadas + app

**Profundidad — decisión de hardware:**

| Opción | Costo | Pros | Contras |
|--------|-------|------|---------|
| **OAK-D Lite** (recomendada) | ~USD 150 | Estéreo + corre YOLO a bordo, un solo dispositivo | Precio |
| ESP32-CAM + ToF VL53L0X | ~USD 15 | Baratísima | ToF mide un punto, no un mapa; hay que apuntar |
| Celular con ARCore | 0 (ya hay APK) | Sin hardware nuevo | Difícil de acoplar al robot |

- [ ] Salida estándar del módulo de visión (JSON por WiFi/serial):
  ```json
  {"detecciones": [{"clase": "maduro", "conf": 0.91, "x": 0.12, "y": -0.05, "z": 0.34}]}
  ```
  (x, y, z en metros relativos a la cámara — este JSON es el **contrato** con el brazo en Fase 3)

**App Android (evolución de `isorropia_harvest`):**
- [ ] Pantalla cámara en vivo con cajas de detección y color por clase
- [ ] Contador de granos maduros en cuadro
- [ ] Modo "captura para dataset" (sigue alimentando el modelo)
- Stack sugerido: la misma app actual + TFLite runtime; si la app es webview, alternativa rápida con React Native Vision Camera o app nativa mínima

**Entregable:** app que detecta granos maduros en vivo + módulo que devuelve coordenadas 3D

---

## Fase 3 — Integración (7 sep – 4 oct)

- [ ] Semana 1: montar cámara en el brazo/base, **calibración cámara↔brazo** (transformación de coordenadas: la cámara dice "grano en (x,y,z) desde mí" → el brazo necesita "(x,y,z) desde mi base")
- [ ] Semana 2: pipeline completo: cámara detecta → brazo va → gripper recoge → deposita en canasta
- [ ] Semana 3: manejo de fallos (grano no agarrado → reintento; coordenada inalcanzable → saltar; verificación post-agarre con la misma cámara)
- [ ] Semana 4: pruebas con planta real en matera / rama cortada

**Entregable:** ciclo completo autónomo detectar→recoger en condiciones controladas

---

## Fase 4 — Desplazamiento por cable (5 oct – 8 nov)

### Concepto

Un **cable tensado entre dos árboles** (~1 m, extensible a más) por el que se desplaza un **trole motorizado** que carga el brazo, la cámara y la batería. El robot recorre el cable, se detiene frente a cada zona con granos maduros, cosecha y sigue.

```
 árbol A                                    árbol B
   ║══════════ cable superior (carga) ══════════║
   ║              ┌─────────┐                   ║
   ║              │  TROLE  │ ← motor + encoder ║
   ║              │ batería │                   ║
   ║              └────┬────┘                   ║
   ║═══════ cable inferior (guía) ══════════════║
   ║              [ brazo + cámara ]
```

### Diseño mecánico

| Elemento | Especificación | Nota |
|----------|---------------|------|
| Cable superior | Guaya acero galvanizado 3 mm (o Dyneema 4 mm) | Soporta el peso: brazo ~1 kg + trole ~1 kg + batería ~0.5 kg → dimensionar ×4 seguridad |
| Cable inferior (guía) | Cuerda/guaya 2 mm | **Clave anti-balanceo:** sin él, el brazo oscila al moverse y la cosecha falla |
| Anclajes | Correas de amarre (ratchet) alrededor del tronco + protector | No clavar al árbol; reubicable en minutos |
| Tensor | Turnbuckle (tensor de tornillo) M8 en un extremo | Cable tenso = menos flecha (caída en el centro) |
| Trole | Chasis PETG impreso, 2 ruedas en V con rodamientos 608ZZ sobre el cable superior + 1 guía en el inferior | Los 608ZZ ya están en la BOM |
| Tracción | Motor DC con reductora (torque ≥ 2 kg·cm) y rueda de fricción engomada contra el cable — alternativa: NEMA17 | Fricción es lo más simple; si patina con rocío, cambiar a correa |

### Control

- [ ] ESP32 en el trole (WiFi con el módulo de visión)
- [ ] **Posición:** encoder magnético en la rueda (o conteo de pasos si NEMA17)
- [ ] **Paradas:** la cámara manda "zona con maduros" → trole frena; opcional: marcadores ArUco en cada árbol como referencia absoluta
- [ ] **Seguridad:** fin de carrera físico en ambos extremos + velocidad máx. 0.2 m/s + freno pasivo (el motor con reductora no gira en libre)

### Energía

- [ ] Batería LiPo 3S 2200 mAh o pack 18650 ×3 con BMS → regulador 5-6 V para servos
- [ ] Estimación: ~30-45 min de operación continua; medir en pruebas y dimensionar

### Cronograma

- [ ] Semana 1 (5–11 oct): diseño CAD del trole + compra guaya/tensores/correas
- [ ] Semana 2-3 (12–25 oct): impresión y ensamble del trole, montaje del cable de prueba entre dos postes
- [ ] Semana 4 (26 oct – 1 nov): control de posición y paradas precisas (±2 cm)
- [ ] Semana 5 (2–8 nov): integración con brazo + cámara — desplazarse, detenerse, cosechar

**Entregable:** robot que se desplaza entre 2 árboles y cosecha en cada parada

---

## Pruebas de campo (9 – 29 nov)

- [ ] Instalación en lote de café de la finca
- [ ] Medir: granos/hora, % de maduros correctamente recogidos, falsos positivos, autonomía de batería
- [ ] Lista de mejoras → definir Fase 5+

### Fases futuras (backlog)

- Fase 5: cadena de cables multi-árbol (transferencia de trole entre tramos)
- Fase 6: canasta colectora con vaciado automático
- Fase 7: operación nocturna con iluminación (menos viento, mejor luz controlada)

---

## Riesgos principales

1. **Envío de componentes** — pedir todo en Fase 0, es lo que más demora
2. **Gripper vs. grano de café** — el grano es pequeño y el pedúnculo resiste; el gripper impreso probablemente necesite rediseño (iterar en Fase 1). Plan B: recoger por racimo
3. **Dataset** — la calidad del detector depende 100% de las fotos; seguir la especificación de la Fase 2
4. **Precisión del brazo** — servos hobby tienen juego (±5 mm en la punta); si no alcanza para granos individuales, compensar con verificación visual post-agarre
5. **Balanceo en el cable** — resuelto en diseño con el segundo cable guía; validar en semana 2 de Fase 4

## Cadencia

- Revisión de avance: **cada sábado**
- Al cerrar cada fase: demo grabada en video + commit de todo al repo
