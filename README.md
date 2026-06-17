# pdf-manager

CLI y web UI para gestionar archivos PDF desde la terminal o el navegador.

- Desbloquear PDFs protegidos con contraseña
- Dividir PDFs por páginas individuales o rangos personalizados
- Combinar múltiples PDFs e imágenes PNG/JPG en uno solo
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

Seleccioná opción `1`, arrastrá el PDF a la terminal y escribí la contraseña.

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

### Word PDF — convertir

Arrastrá un documento DOC, DOCX, RTF u ODT para convertirlo a PDF.
Esta opción usa LibreOffice/soffice instalado en el sistema.

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
| `pypdf` | Lectura y escritura de PDFs |
| `Pillow` | Conversión de imágenes PNG/JPG a páginas PDF |
| `rich` | Interfaz de terminal con colores |
| `flask` | Servidor web |
| `gunicorn` | Servidor WSGI para producción |

La conversión de Word a PDF requiere LibreOffice instalado y disponible como `soffice` o `libreoffice`.

---

## Licencia

MIT
