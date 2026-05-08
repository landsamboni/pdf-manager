#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

mkdir -p "$HOME/bin"

cat > "$HOME/bin/pdf-manager" <<EOF
#!/bin/bash
cd "$PROJECT_DIR"
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/pdf-manager.py" "\$@"
EOF

chmod +x "$HOME/bin/pdf-manager"

echo "Listo. Ejecuta: pdf-manager"
echo 'Si no funciona, agrega esto a ~/.zshrc: export PATH="$HOME/bin:$PATH"'