"""
Lógica pura de procesamiento PDF — sin dependencias de consola.
Usada tanto por la CLI como por el servidor web.
"""

import logging
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError

PDF_SUFFIX = ".pdf"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
MERGE_SUFFIXES = {PDF_SUFFIX, *IMAGE_SUFFIXES}
WORD_SUFFIXES = {".doc", ".docx", ".rtf", ".odt"}
LETTER_SIZE = (612, 792)
IMAGE_PAGE_MARGIN = 72
PDF_IMAGE_DPI = 300

CRYPTO_SUPPORT_ERROR = (
    "Falta soporte criptográfico para procesar este PDF. "
    "Reinstalá las dependencias con: .venv/bin/pip install -r requirements.txt"
)


def pdf_processing_error(action: str, error: Exception) -> str:
    """Devuelve un mensaje entendible para errores producidos por pypdf."""
    if isinstance(error, DependencyError):
        return CRYPTO_SUPPORT_ERROR
    return f"{action}: {error}"


def _out_path(src_name: str, suffix: str, directory: Path) -> Path:
    stem = Path(src_name).stem
    base = directory / f"{stem}_{suffix}.pdf"
    if not base.exists():
        return base
    i = 1
    while True:
        candidate = directory / f"{stem}_{suffix}_{i}.pdf"
        if not candidate.exists():
            return candidate
        i += 1


def parse_ranges(spec: str, total_pages: int) -> list[int]:
    pages = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start < 1 or end > total_pages or start > end:
                raise ValueError(f"Rango inválido: {part}")
            pages.extend(range(start, end + 1))
        else:
            n = int(part)
            if n < 1 or n > total_pages:
                raise ValueError(f"Página fuera de rango: {n}")
            pages.append(n)
    return pages


def unlock_pdf_file(src: Path, password: str, out_dir: Path = None) -> tuple[Path | None, str]:
    """Devuelve (ruta_salida, error). ruta_salida es None si hay error."""
    reader = PdfReader(str(src))
    if not reader.is_encrypted:
        return None, "El PDF no está protegido."
    try:
        result = reader.decrypt(password)
    except Exception as e:
        return None, f"Error al descifrar: {e}"
    if result == 0:
        return None, "Contraseña incorrecta."

    dst = _out_path(src.name, "unlocked", out_dir or src.parent)
    try:
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with open(dst, "wb") as f:
            writer.write(f)
    except Exception as e:
        dst.unlink(missing_ok=True)
        return None, pdf_processing_error("No se pudo desbloquear el PDF", e)
    return dst, ""


def split_pdf_file(
    src: Path,
    mode: str,
    spec: str = "",
    password: str = "",
    out_dir: Path = None,
) -> tuple[list[Path], str]:
    """
    mode '1' → una página por archivo
    mode '2' → por rangos (spec = "1-3,5")
    Devuelve (lista_de_salidas, error).
    """
    reader = PdfReader(str(src))
    if reader.is_encrypted:
        if not password:
            return [], "El PDF está protegido. Proporcioná una contraseña."
        try:
            result = reader.decrypt(password)
        except Exception as e:
            return [], f"Error al descifrar: {e}"
        if result == 0:
            return [], "Contraseña incorrecta."

    total = len(reader.pages)
    directory = out_dir or src.parent
    outputs: list[Path] = []

    try:
        if mode == "1":
            for i, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                dst = directory / f"{src.stem}_p{i:03d}.pdf"
                with open(dst, "wb") as f:
                    writer.write(f)
                outputs.append(dst)
        else:
            if not spec.strip():
                return [], "Indicá las páginas a extraer (ej: 1-3, 5)."
            try:
                pages = parse_ranges(spec, total)
            except ValueError as e:
                return [], str(e)
            writer = PdfWriter()
            for n in pages:
                writer.add_page(reader.pages[n - 1])
            dst = _out_path(src.name, "split", directory)
            with open(dst, "wb") as f:
                writer.write(f)
            outputs.append(dst)
    except Exception as e:
        for output in outputs:
            output.unlink(missing_ok=True)
        if "dst" in locals():
            dst.unlink(missing_ok=True)
        return [], pdf_processing_error("No se pudo dividir el PDF", e)

    return outputs, ""


def word_to_pdf_file(src: Path, out_dir: Path = None) -> tuple[Path | None, str]:
    """Convierte documentos Word/Writer a PDF usando LibreOffice/soffice."""
    if src.suffix.lower() not in WORD_SUFFIXES:
        return None, f"Formato no soportado: '{src.name}'. Usá DOC, DOCX, RTF u ODT."

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None, "No encontré LibreOffice/soffice. Instalá LibreOffice para convertir Word a PDF."

    directory = out_dir or src.parent
    dst = _out_path(src.name, "converted", directory)

    with tempfile.TemporaryDirectory(prefix="pdf-manager-word-") as tmp:
        tmp_dir = Path(tmp)
        profile_dir = tmp_dir / "lo-profile"
        try:
            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    f"-env:UserInstallation=file://{profile_dir}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_dir),
                    str(src),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return None, "LibreOffice tardó demasiado convirtiendo el documento."
        except Exception as e:
            return None, f"No se pudo ejecutar LibreOffice: {e}"

        generated = tmp_dir / f"{src.stem}.pdf"
        if result.returncode != 0 or not generated.exists():
            details = (result.stderr or result.stdout or "").strip()
            if details:
                return None, f"No se pudo convertir '{src.name}' a PDF: {details}"
            return None, f"No se pudo convertir '{src.name}' a PDF."

        shutil.move(str(generated), str(dst))

    return dst, ""


def merge_pdf_files(
    files: list[tuple[Path, str]],
    out_dir: Path = None,
) -> tuple[Path | None, str]:
    """
    files: lista de (ruta, contraseña). Contraseña puede ser vacía.
    Acepta PDFs e imágenes PNG/JPG/JPEG; cada imagen se agrega como una página.
    Devuelve (ruta_salida, error).
    """
    if len(files) < 2:
        return None, "Se necesitan al menos 2 archivos para combinar."

    writer = PdfWriter()
    for src, password in files:
        suffix = src.suffix.lower()
        if suffix not in MERGE_SUFFIXES:
            return None, f"Formato no soportado para merge: '{src.name}'."

        if suffix in IMAGE_SUFFIXES:
            err = _add_image_as_pdf_page(writer, src)
            if err:
                return None, err
            continue

        reader = PdfReader(str(src))
        if reader.is_encrypted:
            if not password:
                return None, f"'{src.name}' está protegido. Desbloquealo primero con Unlock."
            try:
                result = reader.decrypt(password)
            except Exception as e:
                return None, f"Error al descifrar '{src.name}': {e}"
            if result == 0:
                return None, f"Contraseña incorrecta para '{src.name}'."
        try:
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            return None, pdf_processing_error(f"No se pudo procesar '{src.name}'", e)

    first = files[0][0]
    dst = _out_path(first.name, "merged", out_dir or first.parent)
    try:
        with open(dst, "wb") as f:
            writer.write(f)
    except Exception as e:
        dst.unlink(missing_ok=True)
        return None, pdf_processing_error("No se pudo crear el PDF combinado", e)
    return dst, ""


def _add_image_as_pdf_page(writer: PdfWriter, src: Path) -> str:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return "Falta la librería Pillow. Instalá las dependencias con: pip install -r requirements.txt"

    try:
        with Image.open(src) as img:
            img = ImageOps.exif_transpose(img)
            page_img = _image_on_letter_page(img)
            pdf_bytes = BytesIO()
            page_img.save(pdf_bytes, format="PDF", resolution=float(PDF_IMAGE_DPI))
    except Exception as e:
        return f"No se pudo convertir la imagen '{src.name}' a PDF: {e}"

    pdf_bytes.seek(0)
    reader = PdfReader(pdf_bytes)
    for page in reader.pages:
        writer.add_page(page)
    return ""


def _image_on_letter_page(img):
    from PIL import Image

    image = _image_on_white_background(img)
    scale = PDF_IMAGE_DPI / 72
    canvas_size = (round(LETTER_SIZE[0] * scale), round(LETTER_SIZE[1] * scale))
    margin = round(IMAGE_PAGE_MARGIN * scale)
    canvas = Image.new("RGB", canvas_size, "white")
    max_width = canvas_size[0] - (margin * 2)
    max_height = canvas_size[1] - (margin * 2)

    ratio = min(max_width / image.width, max_height / image.height)
    target_size = (round(image.width * ratio), round(image.height * ratio))
    if target_size != image.size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)

    x = (canvas_size[0] - image.width) // 2
    y = (canvas_size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _image_on_white_background(img):
    from PIL import Image

    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")
