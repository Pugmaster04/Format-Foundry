"""Bounded raster import, not an editor for native Adobe project structures."""

from __future__ import annotations

import math
import struct
import threading
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from PIL import Image, ImageOps

PDF_INPUT_EXTS = {".pdf", ".ai"}
PHOTOSHOP_INPUT_EXTS = {".psd", ".psb"}
PDF_RASTER_FORMATS = ("png", "jpg", "tiff")
UNSUPPORTED_ADOBE_EXTS = {".eps", ".ps", ".indd", ".indt", ".idml", ".aep", ".aepx", ".prproj", ".fla", ".xd"}
MAX_INPUT_BYTES = 128 * 1024 * 1024
MAX_PAGES = 100
MAX_PAGE_PIXELS = 16_000_000
MAX_TOTAL_PIXELS = 64_000_000
PDF_DPI = 150
# PDFium is not thread safe, even when separate documents are being rendered.
_PDF_LOCK = threading.RLock()


def _pdfium():
    try:
        import pypdfium2
    except ImportError as exc:
        raise RuntimeError(
            "PDF / Illustrator import requires the bundled pypdfium2 renderer. "
            "Update/reinstall Format Foundry, or install requirements.txt in your source-build virtual environment."
        ) from exc
    return pypdfium2


def unsupported_adobe_message(source: Path) -> str:
    return (
        f"{source.suffix.upper()} is not a supported editable Adobe project format. "
        "Export PDF, TIFF, PNG or a supported media file from the originating application first. "
        "Legacy PostScript AI/EPS/PS is not executed; Illustrator AI must be saved with PDF compatibility."
    )


def validate_pdf_header(source: Path) -> None:
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("PDF / AI exceeds the 128 MiB import limit. Split or optimize it first.")
    with source.open("rb") as handle:
        if not handle.read(5).startswith(b"%PDF-"):
            if source.suffix.lower() == ".ai":
                raise ValueError("This Illustrator file is not PDF-compatible. Save it in Illustrator with Create PDF Compatible File enabled, or export PDF/TIFF.")
            raise ValueError("The file does not contain a supported PDF header; changing its extension is not conversion.")


def validate_photoshop(source: Path) -> None:
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("PSD / PSB exceeds the 128 MiB import limit. Export a smaller flattened TIFF first.")
    with source.open("rb") as handle:
        header = handle.read(26)
    if len(header) != 26 or header[:4] != b"8BPS":
        raise ValueError("Not a Photoshop PSD/PSB document; renaming another file does not convert it.")
    version = struct.unpack_from(">H", header, 4)[0]
    expected = 2 if source.suffix.lower() == ".psb" else 1
    if version != expected:
        raise ValueError("Photoshop file header and extension do not match.")
    height, width = struct.unpack_from(">II", header, 14)
    _pixel_budget(width, height, 0)


@contextmanager
def _open_pdf(source: Path):
    validate_pdf_header(source)
    pdfium = _pdfium()
    with _PDF_LOCK:
        try:
            document = pdfium.PdfDocument(str(source))
        except pdfium.PdfiumError as exc:
            raise ValueError("Cannot open this PDF / AI: it may be damaged, encrypted or password-protected. Export an unlocked copy first.") from exc
        try:
            if not 0 < len(document) <= MAX_PAGES:
                raise ValueError(f"PDF / AI import supports 1-{MAX_PAGES} pages. Split the document first.")
            yield document
        finally:
            document.close()


def _pixel_budget(width: float, height: float, total: int) -> int:
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError("Invalid page dimensions.")
    pixels = math.ceil(width) * math.ceil(height)
    if pixels > MAX_PAGE_PIXELS or total + pixels > MAX_TOTAL_PIXELS:
        raise ValueError("Document exceeds the safe raster memory budget. Split it or reduce its dimensions first.")
    return total + pixels


def pdf_frames(source: Path, *, first_only: bool = False, check_cancelled: Callable[[], None] = lambda: None) -> Iterator[Image.Image]:
    check_cancelled()
    with _open_pdf(source) as document:
        scale = PDF_DPI / 72
        total = 0
        for index in range(1 if first_only else len(document)):
            check_cancelled()
            page = document[index]
            try:
                width, height = page.get_size()
                total = _pixel_budget(width * scale, height * scale, total)
                # Do not initialize forms, JavaScript actions or external content.
                bitmap = page.render(scale=scale, may_draw_forms=False, limit_image_cache=True)
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            finally:
                page.close()
            yield image


def first_pdf_image(source: Path) -> Image.Image:
    with closing(pdf_frames(source, first_only=True)) as frames:
        return next(frames)


def pdf_summary(source: Path) -> dict:
    with _open_pdf(source) as document:
        return {"format": "PDF-compatible AI" if source.suffix.lower() == ".ai" else "PDF",
                "pages": len(document), "raster_dpi": PDF_DPI,
                "conversion": "TIFF: all pages; PNG/JPG and Images pipeline: first page only"}


def _save_pages(frames: Iterator[Image.Image], output: Path, fmt: str, check_cancelled: Callable[[], None]) -> None:
    images = []
    try:
        with closing(frames):
            for image in frames:
                images.append(image)
        check_cancelled()
        if fmt == "tiff":
            images[0].save(output, format="TIFF", save_all=True, append_images=images[1:], compression="tiff_deflate", dpi=(PDF_DPI, PDF_DPI))
        else:
            images[0].save(output, format="PDF", save_all=True, append_images=images[1:], resolution=PDF_DPI)
    finally:
        for image in images:
            image.close()


def export_pdf(source: Path, output: Path, fmt: str, *, quality: int = 92, check_cancelled: Callable[[], None] = lambda: None) -> None:
    """TIFF retains all pages; PNG/JPEG deliberately export only page one."""
    check_cancelled()
    if fmt == "pdf":
        with _open_pdf(source) as document:
            check_cancelled()
            document.save(str(output))
    elif fmt == "tiff":
        _save_pages(pdf_frames(source, check_cancelled=check_cancelled), output, fmt, check_cancelled)
    elif fmt in {"png", "jpg"}:
        with first_pdf_image(source) as image:
            check_cancelled()
            options = {"quality": max(1, min(100, quality))} if fmt == "jpg" else {}
            image.save(output, format="JPEG" if fmt == "jpg" else "PNG", **options)
    else:
        raise ValueError("PDF / AI export supports PDF, multipage TIFF, or first-page PNG/JPG. Editable Word or Adobe project export is not supported.")


def tiff_to_pdf(source: Path, output: Path, check_cancelled: Callable[[], None] = lambda: None) -> None:
    def frames():
        with Image.open(source) as opened:
            if opened.format != "TIFF":
                raise ValueError("The file is not a TIFF image.")
            if not 0 < opened.n_frames <= MAX_PAGES:
                raise ValueError(f"TIFF import supports 1-{MAX_PAGES} pages. Split the document first.")
            total = 0
            for index in range(opened.n_frames):
                check_cancelled()
                opened.seek(index)
                total = _pixel_budget(*opened.size, total)
                with ImageOps.exif_transpose(opened) as oriented:
                    if "A" in oriented.getbands():
                        image = Image.new("RGB", oriented.size, "white")
                        image.paste(oriented, mask=oriented.getchannel("A"))
                    else:
                        image = oriented.convert("RGB")
                yield image
    _save_pages(frames(), output, "pdf", check_cancelled)
