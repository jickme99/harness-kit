# harness-kit 2026.09 — kit_manifest generate / classify contracts.
"""The stamper is an enumeration that can fail open: an empty manifest, a missing
version, or a path that escaped the root would classify a project as fully
customised or fully unmodified for the wrong reason. These tests watch those
refusals, plus the three buckets, plus CRLF-as-not-customised.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_manifest():
    path = ROOT / "reference" / "tools" / "kit_manifest.py"
    if not path.is_file():
        path = ROOT / "scripts" / "kit_manifest.py"
    spec = importlib.util.spec_from_file_location("_kit_manifest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def km():
    return load_manifest()


def test_generate_then_classify_all_unmodified(tmp_path, km):
    (tmp_path / "a.md").write_text("hello\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("world\n", encoding="utf-8")
    listing = tmp_path / "list.txt"
    listing.write_text("a.md\nb.md\n", encoding="utf-8")
    manifest = km.generate(listing, tmp_path, "2026.09.3")
    assert manifest["kit_version"] == "2026.09.3"
    assert set(manifest["files"]) == {"a.md", "b.md"}
    result = km.classify(manifest, tmp_path)
    assert result["unmodified"] == ["a.md", "b.md"]
    assert result["customized"] == []
    assert result["missing"] == []
    assert "regenerate in place" in result["note"]


def test_crlf_is_not_a_customisation(tmp_path, km):
    (tmp_path / "a.md").write_bytes(b"hello\n")
    listing = tmp_path / "list.txt"
    listing.write_text("a.md\n", encoding="utf-8")
    manifest = km.generate(listing, tmp_path, "2026.09.3")
    (tmp_path / "a.md").write_bytes(b"hello\r\n")
    result = km.classify(manifest, tmp_path)
    assert result["unmodified"] == ["a.md"]
    assert result["customized"] == []


def test_edit_is_customized_absent_is_missing(tmp_path, km):
    (tmp_path / "keep.md").write_text("same\n", encoding="utf-8")
    (tmp_path / "edit.md").write_text("before\n", encoding="utf-8")
    (tmp_path / "gone.md").write_text("bye\n", encoding="utf-8")
    listing = tmp_path / "list.txt"
    listing.write_text("keep.md\nedit.md\ngone.md\n", encoding="utf-8")
    manifest = km.generate(listing, tmp_path, "2026.09.3")
    (tmp_path / "edit.md").write_text("after\n", encoding="utf-8")
    (tmp_path / "gone.md").unlink()
    result = km.classify(manifest, tmp_path)
    assert result["unmodified"] == ["keep.md"]
    assert result["customized"] == ["edit.md"]
    assert result["missing"] == ["gone.md"]


def test_empty_list_refuses(tmp_path, km):
    listing = tmp_path / "list.txt"
    listing.write_text("# nothing\n\n", encoding="utf-8")
    with pytest.raises(km.KitError, match="names no files"):
        km.generate(listing, tmp_path, "2026.09.3")


def test_empty_version_refuses(tmp_path, km):
    (tmp_path / "a.md").write_text("x\n", encoding="utf-8")
    listing = tmp_path / "list.txt"
    listing.write_text("a.md\n", encoding="utf-8")
    with pytest.raises(km.KitError, match="kit version"):
        km.generate(listing, tmp_path, "  ")


def test_path_escape_in_list_refuses(tmp_path, km):
    listing = tmp_path / "list.txt"
    listing.write_text("../secret.md\n", encoding="utf-8")
    with pytest.raises(km.KitError, match="may not"):
        km.read_list(listing)


def test_classify_refuses_empty_files_and_missing_version(tmp_path, km):
    with pytest.raises(km.KitError, match="lists no files"):
        km.classify({"files": {}, "kit_version": "2026.09.3"}, tmp_path)
    with pytest.raises(km.KitError, match="kit_version"):
        km.classify({"files": {"a.md": "a" * 64}}, tmp_path)
    with pytest.raises(km.KitError, match="sha256"):
        km.classify({"files": {"a.md": "not-a-hash"}, "kit_version": "x"}, tmp_path)


def test_cli_classify_roundtrip(tmp_path, km):
    (tmp_path / "a.md").write_text("ok\n", encoding="utf-8")
    listing = tmp_path / "list.txt"
    listing.write_text("a.md\n", encoding="utf-8")
    out = tmp_path / "manifest.json"
    rc = km.main(["generate", "--list", str(listing), "--root", str(tmp_path),
                  "--version", "2026.09.3", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["kit_version"] == "2026.09.3"
    rc = km.main(["classify", "--manifest", str(out), "--root", str(tmp_path)])
    assert rc == 0
