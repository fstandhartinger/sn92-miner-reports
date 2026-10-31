import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('reports', Path(__file__).resolve().parents[1] / 'artifact_reports.py')
reports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reports)

class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.page = self.root / 'synthetic-report-0123456789abcdef' / 'index.html'
        self.page.parent.mkdir()
        self.body = '<html><head></head><body><h1>Example</h1><p>Visible report.</p></body></html>'
        self.page.write_text(self.body)
        self.state = self.root / '.artifact-ids.json'

    def test_allocate_once_and_reuse_after_rerender(self):
        with patch.object(reports, 'cli', return_value='a#abcdef') as call:
            self.assertEqual(reports.register(self.page, self.state), 'abcdef')
            self.assertEqual(call.call_count, 1)
            self.assertIn('--access', call.call_args.args)
            self.assertIn('public', call.call_args.args)
            marked = self.page.read_text()
            self.assertEqual(marked.count('data-aid="abcdef"'), 1)
            self.assertIn('<p>Visible report.</p>', marked)
            self.assertEqual(reports.register(self.page, self.state), 'abcdef')
            self.assertEqual(self.page.read_text(), marked)
            self.page.write_text(self.body)
            self.assertEqual(reports.register(self.page, self.state), 'abcdef')
            self.assertEqual(call.call_count, 1)
            self.assertEqual(json.loads(self.state.read_text())[self.page.parent.name], 'abcdef')

    def test_embedded_id_recovers_missing_cache_and_attaches_board(self):
        self.page.write_text(self.body.replace('</head>', '<meta name="artifact-id" content="123abc"></head>'))
        with patch.object(reports, 'cli', return_value='') as call:
            self.assertEqual(reports.register(self.page, self.state, ['42', '42']), '123abc')
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.args[:3], ('add-ref','123abc','board=board:42'))

    def test_conflicting_cache_is_rejected(self):
        self.page.write_text(self.body.replace('</head>', '<meta name="artifact-id" content="123abc"></head>'))
        self.state.write_text(json.dumps({self.page.parent.name: 'abcdef'}))
        with patch.object(reports, 'cli') as call:
            with self.assertRaisesRegex(ValueError, 'conflicts'): reports.register(self.page, self.state)
            call.assert_not_called()

    def test_failed_registry_leaves_report_untouched(self):
        with patch.object(reports, 'cli', side_effect=subprocess.CalledProcessError(1, 'artifact')):
            with self.assertRaises(subprocess.CalledProcessError): reports.register(self.page, self.state)
        self.assertEqual(self.page.read_text(), self.body)
        self.assertFalse(self.state.exists())

if __name__ == '__main__': unittest.main()
