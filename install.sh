#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  Instalando pdf-manager..."
echo ""

# Verificar Python 3.10+
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
  echo "  ERROR: Se requiere Python 3.10 o superior (encontrado: $PYTHON_VERSION)"
  exit 1
fi

echo "  Python $PYTHON_VERSION — OK"

# Crear entorno virtual e instalar dependencias
python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

echo "  Dependencias instaladas — OK"

# Crear comando global en ~/bin
mkdir -p "$HOME/bin"

cat > "$HOME/bin/pdf-manager" <<EOF
#!/bin/bash
cd "$PROJECT_DIR"
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/pdf-manager.py" "\$@"
EOF

chmod +x "$HOME/bin/pdf-manager"

echo "  Comando pdf-manager creado en ~/bin — OK"
echo ""

# Verificar si ~/bin ya está en el PATH
if echo "$PATH" | grep -q "$HOME/bin"; then
  echo "  Listo. Ejecuta:"
  echo ""
  echo "    pdf-manager          # modo terminal"
  echo "    pdf-manager --web    # modo navegador"
else
  echo "  Agrega ~/bin al PATH ejecutando:"
  echo ""
  echo "    echo 'export PATH=\"\$HOME/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
  echo ""
  echo "  Luego podrás usar:"
  echo ""
  echo "    pdf-manager          # modo terminal"
  echo "    pdf-manager --web    # modo navegador"
fi

echo ""
