"""Synthetic OPC fixtures exercise package checks, not presentation quality."""

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "skills/research-ppt/scripts/inspect_pptx.py"
spec = importlib.util.spec_from_file_location("inspect_pptx", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def fixture(path, missing=False, accents=False, external=False):
    presentation = f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="rSecond"/><p:sldId id="257" r:id="rFirst"/></p:sldIdLst></p:presentation>'
    relations = f'<Relationships xmlns="{PKG}"><Relationship Id="rFirst" Type="{R}/slide" Target="slides/slide1.xml"/><Relationship Id="rSecond" Type="{R}/slide" Target="slides/slide9.xml"/></Relationships>'
    def slide(text):
        return f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        package.writestr("_rels/.rels", f'<Relationships xmlns="{PKG}"><Relationship Id="rDoc" Type="{R}/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
        package.writestr("ppt/presentation.xml", presentation)
        package.writestr("ppt/_rels/presentation.xml.rels", relations)
        package.writestr("ppt/slides/slide1.xml", slide("Second in presentation order"))
        if not missing:
            package.writestr("ppt/slides/slide9.xml", slide("C\u0302" if accents else "First in presentation order"))
        if external:
            package.writestr("ppt/slides/_rels/slide1.xml.rels", f'<Relationships xmlns="{PKG}"><Relationship Id="rWeb" Type="{R}/hyperlink" Target="https://example.com/source" TargetMode="External"/></Relationships>')


class InspectPptxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "fixture.pptx"

    def tearDown(self):
        self.temp.cleanup()

    def test_presentation_relationships_determine_order(self):
        fixture(self.path)
        result = module.inspect(self.path, expect_slides=2)
        self.assertEqual(result["errors"], [])
        self.assertEqual([slide["part"] for slide in result["slides"]],
                         ["ppt/slides/slide9.xml", "ppt/slides/slide1.xml"])
        self.assertEqual(result["slides"][0]["first_text"], "First in presentation order")

    def test_missing_related_part_fails(self):
        fixture(self.path, missing=True)
        result = module.inspect(self.path)
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("Missing relationship target" in error for error in result["errors"]))

    def test_external_source_link_is_reported_not_fetched(self):
        fixture(self.path, external=True)
        result = module.inspect(self.path)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["external_relationships"][0]["target"], "https://example.com/source")

    def test_accents_trigger_review_without_claiming_render_failure(self):
        fixture(self.path, accents=True)
        result = module.inspect(self.path)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["review_flags"][0]["slide"], 1)
        self.assertIn("U+0302", result["slides"][0]["combining_accents"][0])

    def test_input_bytes_remain_unchanged(self):
        fixture(self.path)
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        module.inspect(self.path)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_expected_slide_count_is_enforced(self):
        fixture(self.path)
        self.assertEqual(module.inspect(self.path, expect_slides=3)["status"], "error")

    def test_cli_cannot_overwrite_input(self):
        fixture(self.path)
        before = self.path.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.path), "--output", str(self.path)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.path.read_bytes())

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            module.resolve_target("ppt/presentation.xml", "../../private-file")

    def test_invalid_zip_is_a_reported_error(self):
        self.path.write_text("not a zip", encoding="utf-8")
        self.assertEqual(module.inspect(self.path)["status"], "error")


if __name__ == "__main__":
    unittest.main()
