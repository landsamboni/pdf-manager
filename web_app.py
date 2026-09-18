"""
Servidor web Flask para PDF Manager.
Se lanza con: python pdf-manager.py --web
"""

import tempfile
import uuid
import zipfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from pdf_core import IMAGE_SUFFIXES, MERGE_SUFFIXES, WORD_SUFFIXES, convert_to_pdf_file, merge_pdf_files, split_pdf_file, unlock_pdf_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

import time

TEMP_DIR = Path(tempfile.mkdtemp(prefix="pdf-manager-web-"))


def _cleanup_old_files(max_age_seconds: int = 3600) -> None:
    """Borra archivos procesados con más de max_age_seconds de antigüedad."""
    now = time.time()
    for f in TEMP_DIR.iterdir():
        try:
            if f.is_file() and (now - f.stat().st_mtime) > max_age_seconds:
                f.unlink(missing_ok=True)
        except FileNotFoundError:
            pass


def create_app() -> Flask:
    template_dir = str(Path(__file__).parent / "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return jsonify(error="Los archivos superan el límite de 200 MB por operación."), 413

    @app.before_request
    def cleanup():
        _cleanup_old_files()

    def save_upload(file, allowed):
        name = secure_filename(file.filename or "")
        if not name or Path(name).suffix.lower() not in allowed:
            raise ValueError("Formato de archivo no soportado para esta operación.")
        path = TEMP_DIR / f"{uuid.uuid4().hex}_{name}"
        file.save(path)
        return path

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify(error=str(error)), 400

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/unlock", methods=["POST"])
    def api_unlock():
        files = request.files.getlist("files") or request.files.getlist("file")
        if not files:
            return jsonify(error="No se recibió ningún archivo."), 400
        password = request.form.get("password", "")
        errors = []
        outputs = []
        # Isolate intermediate files: only the final download is published.
        with tempfile.TemporaryDirectory(prefix="pdf-manager-unlock-") as tmp:
            directory = Path(tmp)
            for index, file in enumerate(files):
                name = secure_filename(file.filename or "")
                if not name or Path(name).suffix.lower() != ".pdf":
                    errors.append(f"{file.filename or 'Archivo'}: usá un PDF.")
                    continue
                upload = directory / f"{index}_{name}"
                file.save(upload)
                dst, error = unlock_pdf_file(upload, password, out_dir=directory)
                if error:
                    errors.append(f"{file.filename}: {error}")
                else:
                    result = TEMP_DIR / f"{uuid.uuid4().hex}_{Path(name).stem}_unlocked.pdf"
                    result.write_bytes(dst.read_bytes())
                    outputs.append(dict(filename=f"{Path(name).stem}_unlocked.pdf",
                                        source_index=index, download_url=f"/download/{result.name}"))
            if not outputs:
                return jsonify(error="No se pudo desbloquear ningún PDF.", errors=errors), 400
        response = dict(outputs=outputs, errors=errors, processed=len(outputs), total=len(files))
        if len(files) == 1:
            response.update(outputs[0])
        return jsonify(response)

    @app.route("/api/split", methods=["POST"])
    def api_split():
        if "file" not in request.files:
            return jsonify(error="No se recibió ningún archivo."), 400

        f = request.files["file"]
        mode = request.form.get("mode", "1")
        spec = request.form.get("spec", "")
        password = request.form.get("password", "")

        upload = save_upload(f, {".pdf"})

        try:
            outputs, err = split_pdf_file(upload, mode, spec, password, out_dir=TEMP_DIR)
        finally:
            upload.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400

        if len(outputs) == 1:
            return jsonify(filename=outputs[0].name, download_url=f"/download/{outputs[0].name}")

        # Múltiples archivos → ZIP
        zip_name = f"{uuid.uuid4().hex}_{Path(secure_filename(f.filename)).stem}_paginas.zip"
        zip_path = TEMP_DIR / zip_name
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in outputs:
                zf.write(p, p.name)
                p.unlink(missing_ok=True)

        return jsonify(filename=zip_name, download_url=f"/download/{zip_name}")

    @app.route("/api/merge", methods=["POST"])
    def api_merge():
        file_list = request.files.getlist("files")
        if not file_list:
            return jsonify(error="Seleccioná archivos para combinar o una imagen para convertir."), 400

        saved: list[tuple[Path, str]] = []
        try:
            for f in file_list:
                saved.append((save_upload(f, MERGE_SUFFIXES), ""))
            dst, err = merge_pdf_files(saved, out_dir=TEMP_DIR)
        finally:
            for p, _ in saved:
                p.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400
        return jsonify(filename=dst.name, download_url=f"/download/{dst.name}")

    @app.route("/api/convert-to-pdf", methods=["POST"])
    @app.route("/api/word-to-pdf", methods=["POST"])
    def api_word_to_pdf():
        if "file" not in request.files:
            return jsonify(error="No se recibió ningún archivo."), 400

        f = request.files["file"]
        upload = save_upload(f, WORD_SUFFIXES | IMAGE_SUFFIXES)
        try:
            dst, err = convert_to_pdf_file(upload, out_dir=TEMP_DIR)
        finally:
            upload.unlink(missing_ok=True)

        if err:
            return jsonify(error=err), 400
        return jsonify(filename=dst.name, download_url=f"/download/{dst.name}")

    @app.route("/download/<path:filename>")
    def download_file(filename):
        _cleanup_old_files()
        if Path(filename).name != filename or Path(filename).suffix not in {".pdf", ".zip"}:
            return "Archivo no encontrado.", 404
        return send_from_directory(TEMP_DIR, filename, as_attachment=True, download_name=filename)

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
