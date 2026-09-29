import importlib.util
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

import adobe_support as adobe
from backend_support import detect_backend_paths
from modular_file_utility_suite import ConvertTab, OperationCanceledError, TaskEngine

HAS_PDFIUM = importlib.util.find_spec("pypdfium2") is not None


def photoshop_fixture(path: Path, version: int = 1) -> None:
    # A real uncompressed RGB composite: PSD and PSB differ in version and section length.
    header = b"8BPS" + struct.pack(">H6sHIIHH", version, b"\0" * 6, 3, 2, 3, 8, 3)
    path.write_bytes(header + b"\0" * (12 if version == 1 else 16) + b"\0\0" + bytes([200]*6 + [100]*6 + [50]*6))


def engine() -> TaskEngine:
    return TaskEngine(SimpleNamespace(
        backends=SimpleNamespace(imagemagick=None, pandoc=None, libreoffice=None),
        settings={}, resolve_output_path=lambda path, **_: path,
        check_current_task_cancelled=lambda: None,
    ))


class AdobeInputTests(unittest.TestCase):
    def test_pdf_ai_target_filter(self):
        tab = ConvertTab.__new__(ConvertTab)
        self.assertTrue(tab._supported_source_suffix(".psd"))
        self.assertTrue(tab._supported_source_suffix(".psb"))
        self.assertEqual(tab._targets_for_source_suffix(".pdf"), ["png", "jpg", "tiff"])
        self.assertEqual(tab._targets_for_source_suffix(".ai"), ["png", "jpg", "tiff", "pdf"])
        self.assertNotIn("psd", tab._targets_for_source_suffix(".psd"))

    def test_keep_input_only_formats_uses_png(self):
        for suffix in (".psd", ".psb", ".pdf", ".ai"):
            self.assertEqual(TaskEngine._normalized_image_format(Path("test"+suffix), "keep"), "png")

    def test_psd_composite_without_external_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "composite.psd"
            photoshop_fixture(source)
            output = engine().convert_file(source, root, "png", {})
            with Image.open(output) as image:
                self.assertEqual(image.size, (3, 2))
                self.assertEqual(image.getpixel((0, 0)), (200, 100, 50))
            processed = engine().process_image_file(source, root, {"target_format":"keep"})
            self.assertEqual(processed.suffix, ".png")

    def test_psb_missing_backend_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"composite.psb"
            photoshop_fixture(source, 2)
            with self.assertRaisesRegex(RuntimeError, "ImageMagick"):
                engine().convert_file(source, source.parent, "png", {})

    def test_cmyk_psd_can_export_png_without_external_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"cmyk.psd"
            source.write_bytes(b"8BPS"+struct.pack(">H6sHIIHH", 1, b"\0"*6, 4, 2, 3, 8, 4)+b"\0"*14+bytes([200]*24))
            result = engine().convert_file(source, source.parent, "png", {})
            with Image.open(result) as image:
                image.load()
                self.assertEqual(image.mode, "RGB")

    def test_not_photoshop_is_rejected_before_external_process(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"bad.psb"
            source.write_bytes(b"%!PS-Adobe-3.0\nnot a Photoshop file")
            task = engine()
            task.app.backends.imagemagick = "magick"
            task.app.run_process = Mock()
            with self.assertRaisesRegex(ValueError, "Not a Photoshop"):
                task.convert_file(source, source.parent, "png", {})
            task.app.run_process.assert_not_called()

    def test_legacy_ai_rejected_before_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"legacy.ai"
            source.write_text("%!PS-Adobe-3.0")
            with patch.object(adobe, "_pdfium") as loader:
                with self.assertRaisesRegex(ValueError, "PDF-compatible"):
                    adobe.first_pdf_image(source)
                loader.assert_not_called()

    def test_native_projects_explain_export_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in (".indd", ".aep", ".prproj", ".eps"):
                with self.assertRaisesRegex(RuntimeError, "originating application"):
                    engine().convert_document(Path(directory)/("project"+suffix), Path(directory), "pdf")

    def test_resource_bounds(self):
        with self.assertRaisesRegex(ValueError, "memory budget"):
            adobe._pixel_budget(20000, 20000, 0)
        with self.assertRaisesRegex(ValueError, "Invalid page"):
            adobe._pixel_budget(float("nan"), 10, 0)

    def test_photoshop_header_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"large.psd"
            photoshop_fixture(source)
            data = bytearray(source.read_bytes())
            struct.pack_into(">II", data, 14, 30000, 30000)
            source.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "memory budget"):
                adobe.validate_photoshop(source)

    def test_missing_pdfium_error_is_actionable(self):
        with patch.dict("sys.modules", {"pypdfium2": None}):
            with self.assertRaisesRegex(RuntimeError, "Update/reinstall"):
                adobe._pdfium()

    def test_freezer_includes_pdf_renderer(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIn("pypdfium2==5.13.0", (root/"requirements.txt").read_text())
        for name in ("FormatFoundry.spec", "FormatFoundry_Portable.spec"):
            content = (root/name).read_text()
            self.assertIn("'pypdfium2'", content)
            self.assertIn("'pypdfium2_raw'", content)

    def test_notice_collection_keeps_pdfium_dependency_licenses(self):
        from tools.collect_build_evidence import collect_notices
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"requirements.txt").write_text("pypdfium2==5.13.0\n")
            (root/"THIRD_PARTY_NOTICES.txt").write_text("test")
            license_path = Path("pdfium.dist-info/licenses/BUILD_LICENSES/libpng.txt")
            (root/license_path).parent.mkdir(parents=True)
            (root/license_path).write_text("Synthetic notice fixture")
            dist = SimpleNamespace(files=[license_path], requires=[], version="5.13.0",
                                   metadata={"Name":"pypdfium2"}, locate_file=lambda p:root/p)
            with patch("tools.collect_build_evidence.ROOT", root), patch("tools.collect_build_evidence.metadata.distribution", return_value=dist):
                collect_notices(root/"notices")
            self.assertTrue((root/"notices/pypdfium2/0-libpng.txt").is_file())

    def test_cancel_preserves_existing_tiff_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root/"test.pdf", root/"test.tiff"
            output.write_bytes(b"original")
            task = engine()
            task.app.check_current_task_cancelled = Mock(side_effect=OperationCanceledError("stop"))
            with self.assertRaises(OperationCanceledError):
                task.convert_file(source, root, "tiff", {})
            self.assertEqual(output.read_bytes(), b"original")
            self.assertEqual(list(root.glob(".foundry-*")), [])

    def test_failed_pdf_render_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root/"bad.pdf", root/"bad.png"
            source.write_bytes(b"broken")
            output.write_bytes(b"keep")
            with self.assertRaises(ValueError):
                engine().convert_file(source, root, "png", {})
            self.assertEqual(output.read_bytes(), b"keep")
            self.assertEqual(list(root.glob(".foundry-*")), [])

    def test_partial_tiff_to_pdf_failure_keeps_old_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/"test.pdf"
            output.write_bytes(b"keep")

            def fail(source, staged, check):
                staged.write_bytes(b"incomplete")
                raise ValueError("failed")

            with patch("modular_file_utility_suite.tiff_to_pdf", side_effect=fail):
                with self.assertRaises(ValueError):
                    engine().convert_document(root/"test.tiff", root, "pdf")
            self.assertEqual(output.read_bytes(), b"keep")


@unittest.skipUnless(HAS_PDFIUM, "PDFium dependency not installed")
class PdfConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root/"two-pages.pdf"
        self.tiff = self.root/"two-pages.tiff"
        with Image.new("RGB", (72, 48), "red") as first, Image.new("RGB", (72, 48), "blue") as second:
            first.save(self.tiff, "TIFF", save_all=True, append_images=[second])
            first.save(self.pdf, "PDF", save_all=True, append_images=[second], resolution=72)

    def test_all_pdf_pages_to_tiff(self):
        outdir = self.root/"output"
        output = engine().convert_document(self.pdf, outdir, "tiff")
        with Image.open(output) as image:
            self.assertEqual(image.n_frames, 2)
            self.assertEqual(image.size, (150, 100))
            self.assertGreater(image.getpixel((30, 30))[0], 200)
            image.seek(1)
            self.assertGreater(image.getpixel((30, 30))[2], 200)

    def test_pdf_first_page_png_and_jpeg(self):
        for fmt in ("png", "jpg"):
            output = engine().convert_file(self.pdf, self.root/"output", fmt, {})
            with Image.open(output) as image:
                self.assertEqual(image.size, (150, 100))
                self.assertGreater(image.getpixel((30, 30))[0], 200)

    def test_tiff_to_pdf_keeps_pages(self):
        import pypdfium2
        output = engine().convert_document(self.tiff, self.root/"output", "pdf")
        with pypdfium2.PdfDocument(output) as document:
            self.assertEqual(len(document), 2)

    def test_pdf_compatible_ai_path(self):
        ai = self.root/"pdf-compatible.ai"
        ai.write_bytes(self.pdf.read_bytes())
        output = engine().convert_document(ai, self.root/"output", "tiff")
        with Image.open(output) as image:
            self.assertEqual(image.n_frames, 2)
        saved = engine().convert_document(ai, self.root/"output", "pdf")
        self.assertTrue(saved.read_bytes().startswith(b"%PDF-"))

    def test_pdf_images_pipeline_keep_and_resize(self):
        output = engine().process_image_file(self.pdf, self.root/"output", {"target_format":"keep", "max_width":60})
        with Image.open(output) as image:
            self.assertEqual(image.width, 60)

    def test_pdf_metadata_is_document_not_unrecognized_image(self):
        task = engine()
        task.app.backends.ffprobe = None
        result = task.inspect_metadata(self.pdf)
        self.assertEqual(result["document"]["pages"], 2)
        self.assertNotIn("image_error", result)

    def test_pdf_budget_rejection_leaves_no_output(self):
        with patch.object(adobe, "MAX_TOTAL_PIXELS", 16000):
            with self.assertRaisesRegex(ValueError, "memory budget"):
                engine().convert_document(self.pdf, self.root/"output", "tiff")
        self.assertFalse((self.root/"output/two-pages.tiff").exists())

    def test_no_pdf_to_word_claim(self):
        with self.assertRaisesRegex(ValueError, "Editable Word"):
            engine().convert_document(self.pdf, self.root/"output", "docx")

    def test_malformed_pdf_keeps_previous_image(self):
        self.pdf.write_bytes(b"%PDF-1.7\nnot a PDF document")
        output = self.root/"two-pages.png"
        output.write_bytes(b"original")
        with self.assertRaisesRegex(ValueError, "Cannot open"):
            engine().convert_file(self.pdf, self.root, "png", {})
        self.assertEqual(output.read_bytes(), b"original")


class PhotoshopBackendTests(unittest.TestCase):
    def test_real_psb_composite(self):
        executable = detect_backend_paths().get("imagemagick")
        if not executable:
            self.skipTest("ImageMagick not installed")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"real-composite.psb"
            photoshop_fixture(source, 2)
            task = engine()
            task.app.backends.imagemagick = executable
            task.app.run_process = lambda args: subprocess.run(args, check=True, capture_output=True, timeout=30)
            output = task.convert_file(source, source.parent, "png", {})
            with Image.open(output) as image:
                self.assertEqual(image.convert("RGB").getpixel((0, 0)), (200, 100, 50))


if __name__ == "__main__":
    unittest.main()
