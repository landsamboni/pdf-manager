"""
Servidor web Flask para PDF Manager.
Se lanza con: python pdf-manager.py --web
"""

import tempfile
import uuid
import zipfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from pdf_core import merge_pdf_files, split_pdf_file, unlock_pdf_file

import os
import time

TEMP_DIR = Path(tempfile.mkdtemp(prefix="pdf-manager-web-"))


def _cleanup_old_files(max_age_seconds: int = 3600) -> None:
    """Borra archivos procesados con más de max_age_seconds de antigüedad."""
    now = time.time()
    for f in TEMP_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > max_age_seconds:
            f.unlink(missing_ok=True)


def create_app() -> Flask:
    template_dir = str(Path(__file__).parent / "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/unlock", methods=["POST"])
    def api_unlock():
        if "file" not in request.files:
            return jsonify(error="No se recibió ningún archivo."), 400

        f = request.files["file"]
        password = request.form.get("password", "")

        upload = TEMP_DIR / f"{uuid.uuid4().hex}_{f.filename}"
        f.save(str(upload))

        dst, err = unlock_pdf_file(upload, password, out_dir=TEMP_DIR)
        upload.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400
        return jsonify(filename=dst.name, download_url=f"/download/{dst.name}")

    @app.route("/api/split", methods=["POST"])
    def api_split():
        if "file" not in request.files:
            return jsonify(error="No se recibió ningún archivo."), 400

        f = request.files["file"]
        mode = request.form.get("mode", "1")
        spec = request.form.get("spec", "")
        password = request.form.get("password", "")

        upload = TEMP_DIR / f"{uuid.uuid4().hex}_{f.filename}"
        f.save(str(upload))

        outputs, err = split_pdf_file(upload, mode, spec, password, out_dir=TEMP_DIR)
        upload.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400

        if len(outputs) == 1:
            return jsonify(filename=outputs[0].name, download_url=f"/download/{outputs[0].name}")

        # Múltiples archivos → ZIP
        zip_name = f"{Path(f.filename).stem}_paginas.zip"
        zip_path = TEMP_DIR / zip_name
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in outputs:
                zf.write(p, p.name)
                p.unlink(missing_ok=True)

        return jsonify(filename=zip_name, download_url=f"/download/{zip_name}")

    @app.route("/api/merge", methods=["POST"])
    def api_merge():
        file_list = request.files.getlist("files")
        if len(file_list) < 2:
            return jsonify(error="Se necesitan al menos 2 PDFs para combinar."), 400

        saved: list[tuple[Path, str]] = []
        for f in file_list:
            p = TEMP_DIR / f"{uuid.uuid4().hex}_{f.filename}"
            f.save(str(p))
            saved.append((p, ""))

        dst, err = merge_pdf_files(saved, out_dir=TEMP_DIR)

        for p, _ in saved:
            p.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400
        return jsonify(filename=dst.name, download_url=f"/download/{dst.name}")

    @app.route("/download/<path:filename>")
    def download_file(filename):
        _cleanup_old_files()
        file_path = TEMP_DIR / filename
        if not file_path.exists():
            return "Archivo no encontrado.", 404
        return send_file(str(file_path), as_attachment=True, download_name=filename)

    return app


# Expuesto para gunicorn: gunicorn web_app:app
app = create_app()


def run(port: int = 5000) -> None:
    import threading
    import webbrowser

    app = create_app()
    print(f"\n  Servidor iniciado → http://127.0.0.1:{port}")
    print("  Presioná Ctrl+C para detener.\n")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, threaded=True, debug=False)
