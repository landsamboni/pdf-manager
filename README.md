# pdf-manager

CLI y web UI para gestionar archivos PDF desde la terminal o el navegador.

- Desbloquear uno o varios PDFs con una sola contraseña, guardando copias individuales junto a los originales
- Dividir PDFs por páginas individuales o rangos personalizados
- Combinar múltiples PDFs e imágenes PNG/JPG en uno solo
- Convertir una imagen PNG/JPG/JPEG a PDF carta, centrada y sin recortar
- Convertir documentos Word a PDF
- Interfaz web con drag & drop (modo `--web`)

---

## Requisitos

- Python 3.10+
- macOS / Linux

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd pdf-manager
```

### 2. Ejecutar el instalador

```bash
chmod +x install.sh
./install.sh
```

El instalador crea un entorno virtual `.venv`, instala las dependencias y registra el comando `pdf-manager` en `~/bin`.

### 3. Verificar PATH (solo primera vez)

Si al ejecutar `pdf-manager` obtenés "command not found":

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Uso

### Modo CLI (terminal interactiva)

```bash
pdf-manager
```

Muestra un menú con las opciones Unlock, Split y Merge.
También incluye Word PDF para convertir documentos compatibles.

### Modo web (interfaz en el navegador)

```bash
pdf-manager --web
```

Abre automáticamente `http://127.0.0.1:5000` en el navegador.  
Presioná `Ctrl+C` para detener el servidor.

---

## Ejemplos CLI

### Unlock — quitar contraseña

Seleccioná opción `1`, arrastrá todos los PDFs juntos a la terminal y presioná Enter.
Podés agregar más tandas; terminá con Enter vacío y escribí la contraseña una sola vez.
Cada resultado se guarda en la carpeta de su original como `nombre_unlocked.pdf`.
Si ya existe, se agrega un número. Los archivos originales se conservan y no se crea un ZIP.
Los errores se informan por archivo sin detener el resto del lote.

En la web, arrastrá varios PDFs y autorizá su carpeta original, o elegí primero la carpeta
para cargar sus PDFs (podés quitar archivos de la lista). Al pulsar **Quitar contraseña**,
las copias se guardan por separado en esa carpeta. El navegador exige permiso de escritura;
esta función requiere un navegador compatible con `showDirectoryPicker`, como Chrome o Edge.
Si los originales están en carpetas distintas o el navegador no soporta esa función, usá la terminal.
El selector carga los PDFs del nivel principal, omitiendo copias con sufijo `_unlocked`.

### Split — dividir

Rangos válidos:

```
1-3
1,4,7
1-5,8,10-12
```

### Merge — combinar

Arrastrá PDFs, PNGs o JPGs uno por uno. Enter en blanco cuando terminaste la lista.
Las imágenes se agregan como páginas dentro del PDF final.

### Convertir a PDF — imágenes y documentos

Arrastrá un PNG, JPG o JPEG a **Convertir a PDF** (opción `4` en la terminal).
Se genera una hoja carta vertical de 21,59 × 27,94 cm, con la imagen centrada,
proporciones originales y margen mínimo de 2,54 cm. Se respeta la orientación EXIF
y las transparencias se colocan sobre fondo blanco. También funciona con una sola imagen en **Merge**.

Los documentos DOC, DOCX, RTF u ODT siguen usando LibreOffice/soffice instalado en el sistema.

---

## Drag & drop en macOS

Podés arrastrar cualquier archivo PDF o imagen compatible directamente a la ventana de terminal — macOS pega la ruta completa automáticamente.

---

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ejecutar CLI:

```bash
python3 pdf-manager.py
```

Ejecutar servidor web:

```bash
python3 pdf-manager.py --web
```

---

## Estructura del proyecto

```
pdf-manager/
├── pdf-manager.py      # Entrypoint: CLI y arranque del servidor web
├── pdf_core.py         # Lógica de procesamiento PDF (compartida por CLI y web)
├── web_app.py          # Servidor Flask con API REST
├── templates/
│   └── index.html      # Interfaz web
├── requirements.txt
├── Procfile            # Para deploy en plataformas como Render/Heroku
├── install.sh
└── README.md
```

---

## Dependencias

| Paquete | Uso |
|---|---|
| `pypdf[crypto]` | Lectura, escritura y descifrado AES de PDFs |
| `Pillow` | Conversión de imágenes PNG/JPG a páginas PDF |
| `rich` | Interfaz de terminal con colores |
| `flask` | Servidor web |
| `gunicorn` | Servidor WSGI para producción |

La conversión de Word a PDF requiere LibreOffice instalado y disponible como `soffice` o `libreoffice`.

---

## Licencia

MIT

## Pruebas

```bash
.venv/bin/python -m unittest discover -s tests -v
node --test tests/test_web_ui.cjs
```
