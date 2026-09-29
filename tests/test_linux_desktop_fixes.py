import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from display_support import linux_display_bounds
from suite_updater import CURRENT_VERSION, UpdaterApp


class LinuxDesktopFixes(unittest.TestCase):
    def test_pointer_monitor_not_combined_desktop(self):
        text = ('Monitors: 3\n 0: +A 2560/677x1440/381+1920+0 A\n'
                ' 1: +B 1920/470x1080/280+0+0 B\n'
                ' 2: +C 2560/597x1440/336+4480+0 C\n')
        with patch('display_support.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=text)):
            self.assertEqual(linux_display_bounds(7040, 1440, (5000, 300)), (4480, 0, 2560, 1440))
            self.assertEqual(linux_display_bounds(7040, 1440, (500, 300)), (0, 0, 1920, 1080))

    def test_monitor_fallback_is_bounded_and_fits_small_screen(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('xrandr', 1)):
            with patch('display_support.subprocess.run', side_effect=error):
                self.assertEqual(linux_display_bounds(7040, 1440, (0, 0)), (0, 0, 1600, 1000))
                self.assertEqual(linux_display_bounds(800, 600, (0, 0)), (0, 0, 800, 600))

    def test_bundled_probe_never_exposes_expired_executable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            app = UpdaterApp.__new__(UpdaterApp)
            app.runtime_dir = Path(directory)
            (app.runtime_dir / 'FormatFoundry').touch()
            (app.runtime_dir / 'FormatFoundry.exe').touch()
            data = {'app': {'version': CURRENT_VERSION}, 'backends': {'ffmpeg': {
                'detected': True, 'version': '7.0.2', 'path': '/tmp/_MEIgone/imageio_ffmpeg/ffmpeg'}}}
            with patch('suite_updater.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(data))):
                detail = app._app_bundled_ffmpeg_detail()
            self.assertTrue(detail['detected'])
            self.assertEqual(detail['source'], 'app-bundled')
            self.assertEqual(detail['path'], '')
            data['app']['version'] = '1.8.17'
            with patch('suite_updater.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(data))):
                self.assertIsNone(app._app_bundled_ffmpeg_detail())
            for error in (OSError(), subprocess.TimeoutExpired('app', 12)):
                with patch('suite_updater.subprocess.run', side_effect=error):
                    self.assertIsNone(app._app_bundled_ffmpeg_detail())

    def test_absent_app_is_not_reported_as_bundled(self):
        with tempfile.TemporaryDirectory() as directory:
            app = UpdaterApp.__new__(UpdaterApp)
            app.runtime_dir = Path(directory)
            self.assertIsNone(app._app_bundled_ffmpeg_detail())
