# -*- coding: utf-8 -*-
"""不依赖真实样本的判定规则测试。

在项目根目录运行:
    python test/test_detection.py
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "ypMAIN.py")
spec = importlib.util.spec_from_file_location("yx_pesticide", MODULE_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class DetectionTests(unittest.TestCase):
    def test_zero_byte_with_sibling_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "资料"))
            decoy = os.path.join(tmp, "资料.exe")
            open(decoy, "wb").close()
            self.assertTrue(app.is_virus_file(decoy))

    def test_random_exe_without_folder_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            decoy = os.path.join(tmp, "setup.exe")
            with open(decoy, "wb") as f:
                f.write(b"MZ" + b"\x00" * 100)
            self.assertFalse(app.is_virus_file(decoy))

    def test_known_name_without_payload_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            decoy = os.path.join(tmp, "Windows Explorer.exe")
            with open(decoy, "wb") as f:
                f.write(b"MZ" + b"\x00" * 100)
            self.assertFalse(app.is_virus_file(decoy))

    def test_payload_with_sibling_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "资料"))
            decoy = os.path.join(tmp, "资料.exe")
            with open(decoy, "wb") as f:
                f.write(os.urandom(app.VIRUS_SIZE))
            original = app.get_file_head_hash
            app.get_file_head_hash = lambda _path: app.VIRUS_HEAD_MD5
            try:
                self.assertTrue(app.is_virus_file(decoy))
            finally:
                app.get_file_head_hash = original

    def test_version_compare(self):
        self.assertTrue(app.compare_versions("26.8.22.0", "26.8.22.1"))
        self.assertFalse(app.compare_versions("26.8.22.0", "26.8.21.9"))
        self.assertFalse(app.compare_versions("26.8.22.0", "26.8.22.0"))


if __name__ == "__main__":
    unittest.main()
