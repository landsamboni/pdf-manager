import importlib.util
import shlex
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops
from pypdf import PdfReader, PdfWriter

from pdf_core import _image_on_letter_page, convert_to_pdf_file, split_pdf_file, unlock_pdf_file
from web_app import create_app


def pdf_bytes(password=None):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    if password:
        writer.encrypt(password, algorithm="AES-256")
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.patch = patch('web_app.TEMP_DIR', self.directory)
        self.patch.start()
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_png_and_jpeg_produce_one_letter_page(self):
        for extension in ('png', 'jpeg'):
            path = self.directory / f'image.{extension}'
            Image.new('RGB', (120, 80), 'red').save(path)
            output, error = convert_to_pdf_file(path)
            self.assertFalse(error)
            pages = PdfReader(output).pages
            self.assertEqual(len(pages), 1)
            self.assertEqual(tuple(pages[0].mediabox), (0, 0, 612, 792))

    def test_centering_aspect_ratio_and_transparency(self):
        for size in ((120, 80), (80, 120), (1, 10000)):
            page = _image_on_letter_page(Image.new('RGB', size, 'red'))
            bounds = ImageChops.difference(page, Image.new('RGB', page.size, 'white')).getbbox()
            left, top, right, bottom = bounds
            self.assertLessEqual(abs(left - (page.width - right)), 1)
            self.assertLessEqual(abs(top - (page.height - bottom)), 1)
            self.assertGreaterEqual(left, 300)
            self.assertGreaterEqual(top, 300)
        page = _image_on_letter_page(Image.new('RGBA', (40, 40), (0, 0, 0, 0)))
        self.assertEqual(page.getpixel((1275, 1650)), (255, 255, 255))

    def test_single_image_in_conversion_and_merge(self):
        for endpoint, field in (('/api/convert-to-pdf', 'file'), ('/api/merge', 'files')):
            stream = BytesIO()
            Image.new('RGB', (100, 200), 'blue').save(stream, format='PNG')
            stream.seek(0)
            response = self.client.post(endpoint, data={field: (stream, '../../image.PNG')})
            self.assertEqual(response.status_code, 200)
            download = self.client.get(response.json['download_url'])
            self.assertEqual(len(PdfReader(BytesIO(download.data)).pages), 1)
            download.close()

    def test_batch_unlock_shared_password_partial_success_and_duplicate_names(self):
        response = self.client.post('/api/unlock', data={
            'files': [(pdf_bytes('same'), 'doc.pdf'), (pdf_bytes('same'), 'doc.pdf'),
                      (pdf_bytes('different'), 'wrong.pdf'), (BytesIO(b'bad'), 'broken.pdf')],
            'password': 'same',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['processed'], 2)
        self.assertEqual(len(response.json['errors']), 2)
        self.assertEqual(len(response.json['outputs']), 2)
        self.assertEqual(len({item['download_url'] for item in response.json['outputs']}), 2)
        for item in response.json['outputs']:
            download = self.client.get(item['download_url'])
            self.assertFalse(PdfReader(BytesIO(download.data)).is_encrypted)
            download.close()
        self.assertEqual(len(list(self.directory.iterdir())), 2)
        self.assertFalse(list(self.directory.glob('*.zip')))

    def test_unlock_saves_beside_each_original_without_overwrite(self):
        for folder in ('one', 'two'):
            directory = self.directory / folder
            directory.mkdir()
            original = directory / 'document.pdf'
            original.write_bytes(pdf_bytes('same').getvalue())
            existing = directory / 'document_unlocked.pdf'
            existing.write_bytes(b'preserve this')
            output, error = unlock_pdf_file(original, 'same')
            self.assertFalse(error)
            self.assertEqual(output.parent, original.parent)
            self.assertEqual(output.name, 'document_unlocked_1.pdf')
            self.assertEqual(existing.read_bytes(), b'preserve this')
            self.assertTrue(PdfReader(original).is_encrypted)
            self.assertFalse(PdfReader(output).is_encrypted)

    def test_cli_accepts_multiple_dropped_paths_and_asks_password_once(self):
        spec = importlib.util.spec_from_file_location("pdf_manager_cli", Path(__file__).parents[1] / "pdf-manager.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        paths = []
        for folder in ('first folder', 'second folder'):
            directory = self.directory / folder
            directory.mkdir()
            path = directory / 'my document.pdf'
            path.write_bytes(pdf_bytes('shared').getvalue())
            paths.append(path)
        dropped = ' '.join(shlex.quote(str(path)) for path in paths)
        with patch.object(cli.Prompt, 'ask', side_effect=[dropped, '']), \
             patch.object(cli.getpass, 'getpass', return_value='shared') as password, \
             patch.object(cli, 'console'):
            cli.unlock_pdf()
        password.assert_called_once()
        for path in paths:
            output = path.with_name('my document_unlocked.pdf')
            self.assertTrue(output.exists())
            self.assertFalse(PdfReader(output).is_encrypted)
            self.assertTrue(PdfReader(path).is_encrypted)

    def test_single_unlock_backward_compatibility(self):
        response = self.client.post('/api/unlock', data={'file': (pdf_bytes('same'), 'a.pdf'), 'password': 'same'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['filename'].endswith('.pdf'))

    def test_batch_all_fail_leaves_no_files(self):
        response = self.client.post('/api/unlock', data={'files': (pdf_bytes('same'), 'a.pdf'), 'password': 'bad'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_bad_pdf_and_image_return_readable_errors_and_cleanup(self):
        for endpoint, field, name in (('/api/split', 'file', 'bad.pdf'),
                                      ('/api/convert-to-pdf', 'file', 'bad.png')):
            response = self.client.post(endpoint, data={field: (BytesIO(b'broken'), name)})
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.json['error'])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_download_blocks_parent_paths(self):
        response = self.client.get('/download/../outside.pdf')
        self.assertEqual(response.status_code, 404)

    def test_oversized_request_is_json(self):
        self.app.config['MAX_CONTENT_LENGTH'] = 100
        response = self.client.post('/api/unlock', data={'file': (BytesIO(b'x' * 200), 'a.pdf')})
        self.assertEqual(response.status_code, 413)
        self.assertIn('200 MB', response.json['error'])

    def test_split_does_not_overwrite_and_rejects_empty_ranges(self):
        src = self.directory / 'source.pdf'
        src.write_bytes(pdf_bytes().getvalue())
        existing = self.directory / 'source_p001.pdf'
        existing.write_bytes(b'keep me')
        outputs, error = split_pdf_file(src, '1')
        self.assertFalse(error)
        self.assertNotEqual(outputs[0], existing)
        self.assertEqual(existing.read_bytes(), b'keep me')
        outputs, error = split_pdf_file(src, '2', ', ,')
        self.assertTrue(error)
        self.assertFalse(outputs)


if __name__ == '__main__':
    unittest.main()
