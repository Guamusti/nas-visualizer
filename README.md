# 📸 NAS Visualizer

Visualizador de fotos con IA para NAS Ugreen (probado con **DXP4800 Plus**).
Se conecta a tu NAS mediante **WebDAV**, indexa tus fotos en una base de datos
local y las muestra en una interfaz web con filtros por lugar, fecha y carpeta.

Todo corre **en local** — tus fotos nunca salen de tu red.

> **Estado actual: Fase 1** — Conexión, indexación, metadatos EXIF,
> autodetección de lugares por GPS, y galería web con lightbox.
> Las features de IA (caras, objetos) llegan en las Fases 2 y 3.

---

## ✅ Requisitos

- **Python 3.10 o superior** ([descargar](https://www.python.org/downloads/))
- Tu NAS Ugreen encendido y en la misma red
- **WebDAV activado** en el NAS (ver más abajo)

No necesitas Node.js ni nada más: la interfaz web se sirve desde el propio backend.

---

## 🔧 Paso 1 — Activar WebDAV en el NAS

1. Entra en el panel de tu NAS Ugreen (UGOS) desde el navegador.
2. Ve a **Panel de control → Servicios de archivos** (o *File Services*).
3. Activa **WebDAV**. Anota el **puerto** (por defecto suele ser `5005` para HTTP
   o `5006` para HTTPS).
4. Asegúrate de saber la **IP local del NAS** (ej. `192.168.1.100`), tu **usuario**
   y **contraseña**.

---

## 🚀 Paso 2 — Instalar y arrancar

### macOS / Linux

```bash
git clone <url-del-repo> nas-visualizer
cd nas-visualizer
./run.sh
```

La primera vez creará un archivo de configuración y se detendrá pidiéndote
que lo edites. Edita **`backend/.env`** con los datos de tu NAS (ver abajo),
y vuelve a ejecutar `./run.sh`.

### Windows

```bat
git clone <url-del-repo> nas-visualizer
cd nas-visualizer
run.bat
```

Igual que arriba: la primera vez edita `backend\.env` y vuelve a ejecutar `run.bat`.

---

## ⚙️ Paso 3 — Configurar `backend/.env`

Abre `backend/.env` con cualquier editor de texto y rellena:

```ini
NAS_HOST=192.168.1.100      # IP local de tu NAS
NAS_PORT=5005               # Puerto WebDAV
NAS_USE_HTTPS=false         # true si usas el puerto HTTPS (5006)
NAS_USERNAME=tu_usuario
NAS_PASSWORD=tu_contraseña

# Carpeta del NAS a indexar. Ejemplos:
#   /Photos
#   /homes/tu_usuario/Photos
NAS_PHOTOS_PATH=/Photos
```

> 💡 Si no sabes la ruta exacta (`NAS_PHOTOS_PATH`), empieza con `/` para
> indexar todo, o prueba con el nombre de la carpeta compartida donde tienes
> las fotos.

---

## 🖼️ Paso 4 — Usar la app

1. Vuelve a ejecutar `./run.sh` (o `run.bat`).
2. Abre el navegador en **http://localhost:8000**
3. Arriba a la derecha verás si el NAS está **conectado** (punto verde).
4. Pulsa **"Indexar NAS"** — empezará a escanear tus fotos. Verás una barra
   de progreso en tiempo real.
5. A medida que indexa, aparecen las fotos, los lugares detectados por GPS,
   los años y las carpetas en la barra lateral.

La primera indexación puede tardar (descarga cada foto para leer sus metadatos
y generar la miniatura). Las siguientes son mucho más rápidas: solo procesa
las fotos nuevas.

---

## 🗺️ Qué hace ahora mismo

| Función | Descripción |
|---|---|
| **Conexión WebDAV** | Acceso a los archivos del NAS sin tocar nada del sistema |
| **Indexación** | Recorre las carpetas y guarda cada foto en una base de datos local (SQLite) |
| **Metadatos EXIF** | Fecha, cámara, dimensiones, coordenadas GPS |
| **Autodetección de lugares** | Convierte el GPS en "Madrid, España" usando OpenStreetMap (gratis, local) |
| **Miniaturas** | Genera y cachea miniaturas para que la galería vaya rápida |
| **Galería web** | Grid de fotos, filtros por año/lugar/carpeta, ordenación |
| **Álbumes editoriales** | Agrupación automática por país o carpeta, con banderas y portadas difuminadas |
| **Reels** | Recorrido vertical e inmersivo por fotos y vídeos, con reproducción automática silenciosa |
| **Carga progresiva** | Las fotos y reels se incorporan por bloques al desplazarte, sin bloquear la interfaz |
| **Lightbox** | Vista ampliada con todos los metadatos y navegación con teclado (← →) |
| **HEIC / RAW** | Soporte para iPhone (HEIC) y RAW de cámara (CR2/CR3, NEF, ARW, DNG…). Los RAW usan la previsualización JPEG embebida — rápido, sin descomprimir el RAW entero |
| **Indexación rápida** | Procesa 6 fotos en paralelo y cachea el geocoding por zona para no repetir consultas |

---

## 🛣️ Próximas fases

- **Fase 2** — Detección de objetos y animales (YOLOv8): busca "perro", "playa", "coche"…
- **Fase 3** — Reconocimiento de personas: nombra caras y busca "fotos de María"
- **Fase 4** — Vista de mapa, timeline, álbumes automáticos de viajes

---

## 🏗️ Arquitectura

```
NAS Ugreen  ──WebDAV──►  Backend Python  ──►  Interfaz web
(tus fotos)              FastAPI + SQLite      (servida en :8000)
                         indexación + IA
```

- **`backend/`** — API FastAPI, base de datos, servicios de indexación
  - `services/nas_client.py` — conexión WebDAV al NAS
  - `services/exif_extractor.py` — metadatos y miniaturas
  - `services/geocoder.py` — GPS → nombre de lugar
  - `services/indexer.py` — orquesta todo el proceso
  - `routers/` — endpoints de la API
- **`frontend/`** — interfaz web autocontenida (HTML/CSS/JS, sin build)

---

## ❓ Problemas comunes

**"Sin conexión" (punto rojo)**
Revisa que WebDAV esté activado, y que `NAS_HOST`, `NAS_PORT`, usuario y
contraseña en `backend/.env` sean correctos. Prueba a abrir
`http://IP_DEL_NAS:PUERTO` en el navegador.

**No aparece ninguna foto tras indexar**
Comprueba que `NAS_PHOTOS_PATH` apunta a una carpeta que realmente contiene
fotos. Mira la consola donde corre el backend por si hay errores.

**La indexación va lenta**
Descarga cada imagen para leer el GPS y hacer la miniatura, procesando 6 en
paralelo. Para RAW usa la previsualización embebida (rápido). El geocoding
(GPS → lugar) está limitado por OpenStreetMap, pero se cachea por zona, así que
fotos del mismo sitio no repiten consulta. Las siguientes indexaciones solo
tocan fotos nuevas.
