import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError

from pdf_core import (
    merge_pdf_files,
    pdf_processing_error,
    split_pdf_file,
    unlock_pdf_file,
)


class PdfCryptoTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.encrypted_pdf = self.directory / "encrypted.pdf"

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("correcta", algorithm="AES-256")
        with self.encrypted_pdf.open("wb") as stream:
            writer.write(stream)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unlocks_aes_encrypted_pdf(self):
        output, error = unlock_pdf_file(
            self.encrypted_pdf,
            "correcta",
            out_dir=self.directory,
        )

        self.assertEqual(error, "")
        self.assertIsNotNone(output)
        reader = PdfReader(output)
        self.assertFalse(reader.is_encrypted)
        self.assertEqual(len(reader.pages), 1)

    def test_splits_aes_encrypted_pdf(self):
        outputs, error = split_pdf_file(
            self.encrypted_pdf,
            "1",
            password="correcta",
            out_dir=self.directory,
        )

        self.assertEqual(error, "")
        self.assertEqual(len(outputs), 1)
        self.assertFalse(PdfReader(outputs[0]).is_encrypted)

    def test_merges_aes_encrypted_pdf(self):
        plain_pdf = self.directory / "plain.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with plain_pdf.open("wb") as stream:
            writer.write(stream)

        output, error = merge_pdf_files(
            [(self.encrypted_pdf, "correcta"), (plain_pdf, "")],
            out_dir=self.directory,
        )

        self.assertEqual(error, "")
        self.assertIsNotNone(output)
        self.assertEqual(len(PdfReader(output).pages), 2)

    def test_dependency_error_has_recovery_instructions(self):
        message = pdf_processing_error(
            "No se pudo desbloquear el PDF",
            DependencyError("cryptography is required"),
        )

        self.assertIn("Falta soporte criptográfico", message)
        self.assertIn("pip install -r requirements.txt", message)

    def test_unlock_returns_error_instead_of_raising_dependency_error(self):
        with patch("pdf_core.PdfWriter") as writer_class:
            writer_class.return_value.add_page.side_effect = DependencyError(
                "cryptography is required"
            )
            output, error = unlock_pdf_file(
                self.encrypted_pdf,
                "correcta",
                out_dir=self.directory,
            )

        self.assertIsNone(output)
        self.assertIn("Falta soporte criptográfico", error)
        self.assertFalse((self.directory / "encrypted_unlocked.pdf").exists())


if __name__ == "__main__":
    unittest.main()
