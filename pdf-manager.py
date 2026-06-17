#!/usr/bin/env python3
"""
pdf-manager — Unlock, split y merge de PDFs desde la terminal.
"""

import sys
import getpass
import logging

logging.getLogger("pypdf").setLevel(logging.ERROR)

from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
except ImportError:
    print("ERROR: falta la librería 'rich'. Instalala con: pip install rich")
    sys.exit(1)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("ERROR: falta la librería 'pypdf'. Instalala con: pip install pypdf")
    sys.exit(1)

from pdf_core import MERGE_SUFFIXES, PDF_SUFFIX, WORD_SUFFIXES, merge_pdf_files, word_to_pdf_file

console = Console()


# ---------- utilidades ----------

def clean_path(raw: str) -> str:
    """Limpia rutas de drag-and-drop de macOS."""
    p = raw.strip().strip("'").strip('"')
    p = p.replace("\\ ", " ")
    return p


def ask_pdf(prompt: str = "Arrastra el PDF y presiona Enter") -> Path:
    """Pide un PDF al usuario hasta que la ruta sea válida."""
    while True:
        raw = Prompt.ask(f"[cyan]{prompt}[/cyan]")
        if not raw.strip():
            console.print("  [red]✗[/red] Ruta vacía, intenta de nuevo.")
            continue
        path = Path(clean_path(raw))
        if not path.exists():
            console.print(f"  [red]✗[/red] No existe: [dim]{path}[/dim]")
            continue
        if not path.is_file() or path.suffix.lower() != ".pdf":
            console.print(f"  [red]✗[/red] No parece un PDF: [dim]{path}[/dim]")
            continue
        return path


def ask_word(prompt: str = "Arrastra el documento Word y presiona Enter") -> Path:
    """Pide un documento Word/Writer al usuario hasta que la ruta sea válida."""
    while True:
        raw = Prompt.ask(f"[cyan]{prompt}[/cyan]")
        if not raw.strip():
            console.print("  [red]✗[/red] Ruta vacía, intenta de nuevo.")
            continue
        path = Path(clean_path(raw))
        if not path.exists():
            console.print(f"  [red]✗[/red] No existe: [dim]{path}[/dim]")
            continue
        if not path.is_file() or path.suffix.lower() not in WORD_SUFFIXES:
            console.print(f"  [red]✗[/red] No parece un documento Word compatible: [dim]{path}[/dim]")
            continue
        return path


def output_path(src: Path, suffix: str) -> Path:
    """Ruta de salida en la misma carpeta del fuente, sin pisar archivos existentes."""
    base = src.with_name(f"{src.stem}_{suffix}.pdf")
    if not base.exists():
        return base
    i = 1
    while True:
        candidate = src.with_name(f"{src.stem}_{suffix}_{i}.pdf")
        if not candidate.exists():
            return candidate
        i += 1


def parse_ranges(spec: str, total_pages: int) -> list[int]:
    """Convierte '1-3,5,8-10' en [1,2,3,5,8,9,10] (1-indexado)."""
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


def decrypt_reader(reader: PdfReader, filename: str) -> bool:
    """Pide contraseña y descifra el reader. Devuelve True si tuvo éxito."""
    password = getpass.getpass(f"  Contraseña para {filename} (no se mostrará): ")
    try:
        result = reader.decrypt(password)
    except Exception as e:
        console.print(f"  [red]✗[/red] Error al descifrar: {e}")
        return False
    if result == 0:
        console.print("  [red]✗[/red] Contraseña incorrecta.")
        return False
    return True


# ---------- operaciones ----------

def unlock_pdf():
    console.print(Panel("[bold yellow]UNLOCK[/bold yellow] — Quitar contraseña de un PDF", style="yellow"))
    src = ask_pdf()
    reader = PdfReader(str(src))

    if not reader.is_encrypted:
        console.print("  [blue]ℹ[/blue] El PDF no está protegido. Nada que hacer.")
        return

    if not decrypt_reader(reader, src.name):
        return

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    dst = output_path(src, "unlocked")
    with open(dst, "wb") as f:
        writer.write(f)
    console.print(f"  [green]✓[/green] PDF desbloqueado: [bold]{dst.name}[/bold]")
    console.print(f"  [dim]Guardado en: {dst.parent}[/dim]")


def split_pdf():
    console.print(Panel("[bold cyan]SPLIT[/bold cyan] — Dividir un PDF", style="cyan"))
    src = ask_pdf()
    reader = PdfReader(str(src))

    if reader.is_encrypted:
        if not decrypt_reader(reader, src.name):
            return

    total = len(reader.pages)
    console.print(f"\n  El PDF tiene [bold]{total}[/bold] páginas.\n")

    table = Table(show_header=False, box=None, padding=(0, 4))
    table.add_row("[bold yellow]1[/bold yellow]", "Una página por archivo")
    table.add_row("[bold yellow]2[/bold yellow]", "Por rangos  [dim](ej: 1-3,5,8-10)[/dim]")
    console.print(table)
    console.print()

    mode = Prompt.ask("  [cyan]Modo[/cyan]", choices=["1", "2"])

    if mode == "1":
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Extrayendo páginas...", total=total)
            for i, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                dst = output_path(src, f"p{i:03d}")
                with open(dst, "wb") as f:
                    writer.write(f)
                progress.advance(task)
        console.print(f"\n  [green]✓[/green] {total} archivos creados en [bold]{src.parent}[/bold]")

    else:
        spec = Prompt.ask("  [cyan]Páginas a extraer[/cyan]")
        try:
            pages = parse_ranges(spec, total)
        except ValueError as e:
            console.print(f"  [red]✗[/red] {e}")
            return
        writer = PdfWriter()
        for n in pages:
            writer.add_page(reader.pages[n - 1])
        dst = output_path(src, "split")
        with open(dst, "wb") as f:
            writer.write(f)
        console.print(f"  [green]✓[/green] PDF generado: [bold]{dst.name}[/bold]")
        console.print(f"  [dim]Guardado en: {dst.parent}[/dim]")


def merge_pdf():
    console.print(Panel("[bold magenta]MERGE[/bold magenta] — Combinar PDFs e imágenes", style="magenta"))
    console.print("  Arrastra PDFs, PNGs o JPGs uno por uno. [dim]Enter en blanco para terminar.[/dim]\n")

    files: list[Path] = []
    idx = 1
    while True:
        raw = Prompt.ask(f"  [cyan]Archivo #{idx}[/cyan]", default="")
        if not raw.strip():
            if not files:
                console.print("  [dim]Sin archivos. Volviendo al menú.[/dim]")
                return
            break
        path = Path(clean_path(raw))
        if not path.exists() or path.suffix.lower() not in MERGE_SUFFIXES:
            console.print(f"    [red]✗[/red] No válido: [dim]{path}[/dim]")
            continue
        files.append(path)
        console.print(f"    [green]✓[/green] [dim]{path.name}[/dim]")
        idx += 1

    if len(files) < 2:
        console.print("  [red]✗[/red] Necesitás al menos 2 archivos para combinar.")
        return

    merge_inputs: list[tuple[Path, str]] = []
    for f in files:
        password = ""
        if f.suffix.lower() != PDF_SUFFIX:
            merge_inputs.append((f, password))
            continue

        reader = PdfReader(str(f))
        if reader.is_encrypted:
            password = getpass.getpass(f"  Contraseña para {f.name} (no se mostrará): ")
            try:
                result = reader.decrypt(password)
            except Exception as e:
                console.print(f"  [red]✗[/red] Error al descifrar: {e}")
                return
            if result == 0:
                console.print("  [red]✗[/red] Contraseña incorrecta.")
                return
        merge_inputs.append((f, password))

    dst, err = merge_pdf_files(merge_inputs)
    if err:
        console.print(f"  [red]✗[/red] {err}")
        return
    console.print(f"\n  [green]✓[/green] PDF combinado: [bold]{dst.name}[/bold]")
    console.print(f"  [dim]Guardado en: {dst.parent}[/dim]")


def word_to_pdf():
    console.print(Panel("[bold green]WORD → PDF[/bold green] — Convertir documento Word a PDF", style="green"))
    src = ask_word()

    dst, err = word_to_pdf_file(src)
    if err:
        console.print(f"  [red]✗[/red] {err}")
        return

    console.print(f"  [green]✓[/green] PDF generado: [bold]{dst.name}[/bold]")
    console.print(f"  [dim]Guardado en: {dst.parent}[/dim]")


# ---------- menú principal ----------

def menu():
    while True:
        console.print()
        menu_text = Text()
        menu_text.append("  1  ", style="bold yellow")
        menu_text.append("Unlock   ", style="yellow")
        menu_text.append("quitar contraseña\n", style="dim")
        menu_text.append("  2  ", style="bold cyan")
        menu_text.append("Split    ", style="cyan")
        menu_text.append("dividir en páginas\n", style="dim")
        menu_text.append("  3  ", style="bold magenta")
        menu_text.append("Merge    ", style="magenta")
        menu_text.append("combinar PDFs e imágenes\n", style="dim")
        menu_text.append("  4  ", style="bold green")
        menu_text.append("Word PDF ", style="green")
        menu_text.append("convertir Word a PDF\n", style="dim")
        menu_text.append("  0  ", style="bold red")
        menu_text.append("Salir", style="red")

        console.print(Panel(
            menu_text,
            title="[bold white] PDF MANAGER [/bold white]",
            border_style="bright_white",
            padding=(1, 3),
        ))

        choice = Prompt.ask("[bold]Opción[/bold]", choices=["0", "1", "2", "3", "4"])

        if choice == "1":
            unlock_pdf()
        elif choice == "2":
            split_pdf()
        elif choice == "3":
            merge_pdf()
        elif choice == "4":
            word_to_pdf()
        elif choice == "0":
            console.print("\n[dim]Chau. 👋[/dim]\n")
            break
        else:
            continue

        console.print()
        console.rule("[dim]─[/dim]")
        console.input("\n  Presiona [bold]Enter[/bold] para volver al menú... ")


if __name__ == "__main__":
    if "--web" in sys.argv:
        try:
            from web_app import run as run_web
        except ImportError:
            console.print("[red]ERROR:[/red] falta Flask. Instalalo con: pip install flask")
            sys.exit(1)
        run_web()
    else:
        try:
            menu()
        except KeyboardInterrupt:
            console.print("\n[dim]Interrumpido. Chau.[/dim]\n")
            sys.exit(0)
