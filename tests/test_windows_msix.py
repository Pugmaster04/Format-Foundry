import base64
import hashlib
import io
import json
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import quote

from PIL import Image

from app_identity import PACKAGE_VERSION
from modular_file_utility_suite import SuiteApp
from suite_updater import UpdaterApp
from tools.build_msix_package import (
    BLOCKMAP,
    LOGOS,
    UNSIGNED_OID,
    manifest_bytes,
    msix_version,
    package_identity,
    validate_msix,
)
from windows_package_support import (
    WINDOWS_UNINSTALL_URI,
    WindowsPackage,
    format_foundry_package,
    migrate_legacy_settings,
    packaged_settings_root,
)


class MSIXBuildTests(unittest.TestCase):
    def test_store_versions_require_positive_major_and_zero_revision(self):
        self.assertEqual(msix_version("0.7.1-beta"), "1.7.1.0")
        self.assertEqual(msix_version("0.7.1-beta", "1.7.2.0"), "1.7.2.0")
        for invalid in ("0.7.1.0", "1.7.1.2", "1.65536.1.0", "-1.7.1.0", "1.7.beta.0"):
            with self.assertRaises(ValueError):
                msix_version("0.7.1-beta", invalid)

    def test_store_identity_is_required_and_test_identity_cannot_be_submitted(self):
        candidate = package_identity("candidate")
        self.assertIn(UNSIGNED_OID, candidate["publisher"])
        with self.assertRaises(ValueError):
            package_identity("store", candidate)
        with self.assertRaises(ValueError):
            package_identity("store")
        identity = {
            "package_name": "12345Publisher.FormatFoundry", "publisher": "CN=01234567-89ab-cdef-0123-456789abcdef",
            "publisher_display_name": "Publisher & Tools", "store_product_id": "9TEST1234567",
        }
        self.assertEqual(package_identity("store", identity), identity)
        root = ET.fromstring(manifest_bytes(identity, "1.7.1.0"))
        self.assertIn("Publisher & Tools", "".join(root.itertext()))

    @staticmethod
    def write_test_package(path, *, corrupt=False, omit_block=False):
        identity = package_identity("candidate")
        pe = bytearray(128)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 60, 64)
        pe[64:68] = b"PE\0\0"
        struct.pack_into("<H", pe, 68, 0x8664)
        files = {
            "AppxManifest.xml": manifest_bytes(identity, "1.7.1.0"),
            "App/FormatFoundry.exe": bytes(pe), "App/FormatFoundry_Updater.exe": bytes(pe),
            "App/msix-distribution.json": json.dumps({"channel": "development", "package_version": PACKAGE_VERSION}).encode(),
            "App/msix-build-source.json": json.dumps({"payload_source_sha256": "0" * 64}).encode(),
            "App/_internal/LICENSE": b"test terms", "App/_internal/THIRD_PARTY_NOTICES.txt": b"test notices",
            "App/_internal/assets/code_languages.json": b"{}",
            "App/multiblock+data.bin": b"a" * 70000,
        }
        for name, size in LOGOS.items():
            output = io.BytesIO()
            Image.new("RGBA", (size, size)).save(output, format="PNG")
            files[f"Assets/{name}"] = output.getvalue()
        blockmap = ET.Element(f"{{{BLOCKMAP}}}BlockMap", {"HashMethod": "http://www.w3.org/2001/04/xmlenc#sha256"})
        for name, content in files.items():
            if omit_block and name == "App/multiblock+data.bin":
                continue
            file = ET.SubElement(blockmap, f"{{{BLOCKMAP}}}File", {"Name": name.replace("/", "\\"), "Size": str(len(content))})
            for offset in range(0, len(content), 65536):
                digest = hashlib.sha256(content[offset:offset + 65536]).digest()
                ET.SubElement(file, f"{{{BLOCKMAP}}}Block", {"Hash": base64.b64encode(digest).decode()})
        if corrupt:
            files["App/multiblock+data.bin"] = b"b" * 70000
        with zipfile.ZipFile(path, "w") as output:
            for name, content in files.items():
                output.writestr(quote(name, safe="/[]"), content)
            output.writestr("AppxBlockMap.xml", ET.tostring(blockmap))
            output.writestr("[Content_Types].xml", b"test")
        return identity

    def test_package_validator_checks_real_blocks_and_complete_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.msix"
            identity = self.write_test_package(path)
            report = validate_msix(path, identity, "1.7.1.0", "candidate")
            self.assertGreater(report["verified_blockmap_files"], 8)
            self.assertFalse(report["store_certified"])
            for arguments in ({"corrupt": True}, {"omit_block": True}):
                self.write_test_package(path, **arguments)
                with self.assertRaises(ValueError):
                    validate_msix(path, identity, "1.7.1.0", "candidate")


class WindowsPackageRuntimeTests(unittest.TestCase):
    def setUp(self):
        format_foundry_package.cache_clear()

    def tearDown(self):
        format_foundry_package.cache_clear()

    def test_source_run_under_store_python_is_not_treated_as_our_package(self):
        with patch("windows_package_support.sys.frozen", False, create=True), patch("windows_package_support.current_package_identity") as query:
            self.assertIsNone(format_foundry_package())
            query.assert_not_called()

    def test_frozen_package_without_metadata_still_cannot_self_replace(self):
        with tempfile.TemporaryDirectory() as temporary:
            identity = WindowsPackage("FormatFoundry.Development_test", "full_name", Path(temporary))
            with patch("windows_package_support.sys.frozen", True, create=True), patch("windows_package_support.sys.executable", "FormatFoundry.exe"), patch("windows_package_support.current_package_identity", return_value=identity):
                self.assertEqual(format_foundry_package(), identity)

    def test_settings_migrate_once_without_modifying_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary)
            identity = WindowsPackage("FormatFoundry.Development_test", "full_name", local / "install")
            original = local / "FormatFoundry" / "settings.json"
            original.parent.mkdir()
            original.write_text('{"dark_mode": true}', encoding="utf-8")
            with patch("windows_package_support.format_foundry_package", return_value=identity), patch("windows_package_support.windows_local_appdata", return_value=local):
                root = packaged_settings_root()
                self.assertIsNotNone(root)
                migrate_legacy_settings(root, "settings.json")
                destination = root / "FormatFoundry" / "settings.json"
                self.assertEqual(destination.read_bytes(), original.read_bytes())
                destination.write_text('{"dark_mode": false}', encoding="utf-8")
                migrate_legacy_settings(root, "settings.json")
                self.assertEqual(destination.read_text(), '{"dark_mode": false}')
                self.assertEqual(original.read_text(), '{"dark_mode": true}')

    def test_packaged_uninstall_does_not_choose_registered_exe_uninstaller(self):
        app = SuiteApp.__new__(SuiteApp)
        app.settings_path = Path("settings.json")
        app.default_output_root = Path("output")
        identity = WindowsPackage("family", "full", Path("install"))
        with patch("modular_file_utility_suite.format_foundry_package", return_value=identity), patch.object(app, "_resolve_windows_uninstall_command") as legacy:
            plan = app._build_uninstall_plan()
            self.assertEqual(plan.launch_uri, WINDOWS_UNINSTALL_URI)
            self.assertIsNone(plan.launch_command)
            legacy.assert_not_called()

    def test_main_app_store_updates_skip_network_and_startup_dialog(self):
        app = SuiteApp.__new__(SuiteApp)
        with patch("modular_file_utility_suite.format_foundry_package", return_value=Mock()), patch("modular_file_utility_suite.open_store_updates") as store, patch.object(app, "_launch_updater") as updater:
            app._run_startup_update_flow()
            self.assertTrue(app._startup_update_flow_handled)
            app._check_updates_in_background(interactive=False)
            store.assert_not_called()
            app._open_updater_for_updates()
            store.assert_called_once()
            updater.assert_not_called()

    def test_updater_store_actions_cannot_launch_downloaded_exe(self):
        app = UpdaterApp.__new__(UpdaterApp)
        app._open_store_updates = Mock()
        with patch("suite_updater.format_foundry_package", return_value=Mock()), patch("suite_updater.subprocess.Popen") as execute:
            app._check_updates_clicked()
            app._download_update_clicked()
            app._open_download_link()
            app._offer_verified_package_action(Path("installer.exe"))
            self.assertEqual(app._open_store_updates.call_count, 4)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
