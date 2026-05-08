# pdf-manager

Utilidad de terminal para gestionar PDFs: desbloquear, dividir y combinar.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python3 pdf-manager.py
```

Podés arrastrar archivos PDF directo a la terminal (drag & drop funciona en macOS).

## Funciones

| Opción | Descripción |
|--------|-------------|
| **Unlock** | Quita la contraseña de un PDF protegido |
| **Split** | Divide un PDF por páginas individuales o por rangos (`1-3,5,8-10`) |
| **Merge** | Combina múltiples PDFs en uno solo |

## Requisitos

- Python 3.10+
- `pypdf` — lectura/escritura de PDFs
- `rich` — interfaz con colores en la terminal
