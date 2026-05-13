"""
Lógica pura de procesamiento PDF — sin dependencias de consola.
Usada tanto por la CLI como por el servidor web.
"""

import logging
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader, PdfWriter


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

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    dst = _out_path(src.name, "unlocked", out_dir or src.parent)
    with open(dst, "wb") as f:
        writer.write(f)
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

    return outputs, ""


def merge_pdf_files(
    files: list[tuple[Path, str]],
    out_dir: Path = None,
) -> tuple[Path | None, str]:
    """
    files: lista de (ruta, contraseña). Contraseña puede ser vacía.
    Devuelve (ruta_salida, error).
    """
    if len(files) < 2:
        return None, "Se necesitan al menos 2 PDFs para combinar."

    writer = PdfWriter()
    for src, password in files:
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
        for page in reader.pages:
            writer.add_page(page)

    first = files[0][0]
    dst = _out_path(first.name, "merged", out_dir or first.parent)
    with open(dst, "wb") as f:
        writer.write(f)
    return dst, ""
