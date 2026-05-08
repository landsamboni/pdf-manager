# pdf-manager

CLI minimalista para gestionar archivos PDF desde la terminal.

Permite:

- 🔓 Desbloquear PDFs protegidos con contraseña
- ✂️ Dividir PDFs por páginas o rangos
- 📚 Combinar múltiples PDFs
- 🖥️ Usar drag & drop directamente desde macOS Terminal

---

## Características

| Función | Descripción |
|---|---|
| **Unlock** | Elimina la contraseña de un PDF protegido |
| **Split** | Divide un PDF en páginas individuales o por rangos personalizados |
| **Merge** | Combina múltiples PDFs en un único archivo |

---

## Requisitos

- Python 3.10+
- macOS / Linux

Dependencias:

- `pypdf`
- `rich`

---

# Instalación

## 1. Clonar el repositorio

```bash
git clone <repo-url>
cd pdf-manager
```

---

## 2. Ejecutar el instalador

```bash
chmod +x install.sh
./install.sh
```

El instalador automáticamente:

- crea un entorno virtual (`.venv`)
- instala dependencias
- crea el comando global `pdf-manager`

---

## 3. Verificar PATH (solo primera vez)

Si el comando no funciona:

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

# Uso

Ejecutar desde cualquier directorio:

```bash
pdf-manager
```

---

## Ejemplos

### Desbloquear PDF

Seleccionar:

```text
1 -> Unlock
```

Ingresar:

- archivo PDF
- contraseña
- nombre de salida

---

### Dividir PDF

Ejemplos de rangos válidos:

```text
1-3
1,4,7
1-5,8,10-12
```

---

### Combinar PDFs

Seleccionar múltiples archivos PDF y generar un único documento final.

---

## Drag & Drop en macOS

Podés arrastrar archivos PDF directamente a la terminal.

macOS automáticamente pegará la ruta completa del archivo.

---

## Estructura del proyecto

```text
pdf-manager/
├── install.sh
├── pdf-manager.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Desarrollo

Crear entorno virtual manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ejecutar localmente:

```bash
python3 pdf-manager.py
```

---

## Próximas mejoras

- [ ] Compresión de PDFs
- [ ] Rotación de páginas
- [ ] Extraer páginas específicas
- [ ] Conversión imágenes → PDF
- [ ] Empaquetado como comando real (`pipx` / Homebrew)

---

## Licencia

MIT
