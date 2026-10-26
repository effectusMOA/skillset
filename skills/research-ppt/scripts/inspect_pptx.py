#!/usr/bin/env python3
"""Read-only OOXML inspection. This is not a renderer or a research reviewer."""

import argparse
from collections import Counter
import json
from pathlib import Path
import posixpath
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def source_part(rels_part):
    if rels_part == "_rels/.rels":
        return ""
    directory, filename = posixpath.split(rels_part)
    return posixpath.join(posixpath.dirname(directory), filename[:-5])


def rels_part(part):
    directory, filename = posixpath.split(part)
    return posixpath.join(directory, "_rels", filename + ".rels")


def resolve_target(source, target):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        raise ValueError("Internal relationship contains an external URL")
    decoded = unquote(parsed.path)
    resolved = posixpath.normpath(
        decoded.lstrip("/") if decoded.startswith("/")
        else posixpath.join(posixpath.dirname(source), decoded)
    )
    if resolved in ("", ".", "..") or resolved.startswith("../") or "\\" in resolved:
        raise ValueError("Relationship target is outside the package")
    return resolved


def paragraphs(root):
    result = []
    for element in root.iter():
        if local_name(element.tag) != "p":
            continue
        # DrawingML paragraphs are leaf containers for text runs. Ignore other p tags.
        if "drawingml" not in element.tag:
            continue
        chunks = []
        for child in element.iter():
            name = local_name(child.tag)
            if name == "t":
                chunks.append(child.text or "")
            elif name == "br":
                chunks.append("\n")
        value = "".join(chunks).strip()
        if value:
            result.append(value)
    return result


def inspect(path, expect_slides=None):
    report = {
        "file": str(Path(path).resolve()),
        "status": "error",
        "errors": [],
        "review_flags": [],
        "slides": [],
        "limits": [
            "No rendering, visual fit, equation correctness or citation verification.",
            "Object counts do not prove practical editability or font availability.",
        ],
    }
    errors = report["errors"]
    try:
        with zipfile.ZipFile(path) as package:
            names_list = package.namelist()
            names = set(names_list)
            duplicate_names = [name for name, count in Counter(names_list).items() if count > 1]
            if duplicate_names:
                errors.append("Duplicate ZIP entries: " + ", ".join(sorted(duplicate_names)))
            bad_part = package.testzip()
            if bad_part:
                errors.append("CRC failure: " + bad_part)
            if "[Content_Types].xml" not in names:
                errors.append("Missing [Content_Types].xml")

            relationships = {}
            external = []
            for entry in sorted(n for n in names if n.endswith(".rels")):
                source = source_part(entry)
                if source and source not in names:
                    errors.append("Relationships without source part: " + entry)
                mapping = {}
                try:
                    root = ET.fromstring(package.read(entry))
                    for relation in root:
                        rid = relation.get("Id")
                        target = relation.get("Target")
                        if not rid or not target:
                            errors.append("Missing relationship Id or Target: " + entry)
                            continue
                        if rid in mapping:
                            errors.append("Duplicate relationship Id: " + entry + " / " + rid)
                        info = dict(type=relation.get("Type", ""), external=False, target=target)
                        if relation.get("TargetMode") == "External":
                            info["external"] = True
                            external.append(dict(source=source, id=rid, target=target))
                        else:
                            try:
                                info["target"] = resolve_target(source, target)
                                if info["target"] not in names:
                                    errors.append("Missing relationship target: " + source + " -> " + info["target"])
                            except ValueError as exc:
                                errors.append(str(exc) + ": " + entry + " / " + rid)
                        mapping[rid] = info
                    relationships[source] = mapping
                except ET.ParseError as exc:
                    errors.append("Malformed relationships XML: " + entry + " / " + str(exc))

            report["external_relationships"] = external
            office = [r for r in relationships.get("", {}).values()
                      if r["type"].endswith("/officeDocument") and not r["external"]]
            if len(office) != 1:
                errors.append("Expected one internal officeDocument relationship")
                return report
            presentation_part = office[0]["target"]
            if presentation_part not in names:
                return report
            root = ET.fromstring(package.read(presentation_part))
            if local_name(root.tag) != "presentation":
                errors.append("officeDocument is not a presentation")
                return report
            presentation_rels = relationships.get(presentation_part, {})
            slide_ids = [element for element in root.iter() if local_name(element.tag) == "sldId"]
            report["slide_count"] = len(slide_ids)
            if expect_slides is not None and len(slide_ids) != expect_slides:
                errors.append(f"Expected {expect_slides} slides, found {len(slide_ids)}")
            seen_slide_parts = set()
            for number, slide_id in enumerate(slide_ids, 1):
                rid = next((value for key, value in slide_id.attrib.items()
                            if key.startswith("{") and local_name(key) == "id"), None)
                relation = presentation_rels.get(rid)
                if not relation or relation["external"] or not relation["type"].endswith("/slide"):
                    errors.append(f"Slide {number} has no valid internal slide relationship: {rid}")
                    continue
                part = relation["target"]
                if part not in names:
                    continue
                if part in seen_slide_parts:
                    errors.append("Repeated slide part in presentation order: " + part)
                seen_slide_parts.add(part)
                slide_root = ET.fromstring(package.read(part))
                text_paragraphs = paragraphs(slide_root)
                text = "\n".join(text_paragraphs)
                nodes = list(slide_root.iter())
                counts = Counter(local_name(element.tag) for element in nodes)
                fonts = sorted({element.get("typeface") for element in nodes
                                if local_name(element.tag) in ("latin", "ea", "cs")
                                and element.get("typeface")})
                flags = []
                combining = sorted({f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')}"
                                    for ch in text if 0x0300 <= ord(ch) <= 0x036F})
                if combining:
                    flags.append("Combining accents: verify hats/bars in the final render")
                if "\ufffd" in text:
                    flags.append("Replacement character U+FFFD appears in text")
                if re.search(r"\\(?:hat|widehat|bar|frac|argmin)\b", text):
                    flags.append("Literal math command: verify it is not an unrendered equation")
                locks = []
                for element in nodes:
                    if local_name(element.tag).endswith("Locks"):
                        locks.extend(key for key, value in element.attrib.items()
                                     if value in ("1", "true"))
                if locks:
                    flags.append("DrawingML locks exist: inspect editing behavior before changing them")
                if counts["pic"] and not text_paragraphs:
                    flags.append("Pictures with no extracted text: inspect content and editability")
                notes = []
                for note in relationships.get(part, {}).values():
                    if note["type"].endswith("/notesSlide") and not note["external"] and note["target"] in names:
                        notes.extend(paragraphs(ET.fromstring(package.read(note["target"]))))
                info = dict(number=number, part=part, first_text=text_paragraphs[0] if text_paragraphs else "",
                            paragraphs=text_paragraphs, notes=notes,
                            text_shapes=counts["sp"], pictures=counts["pic"], tables=counts["tbl"],
                            charts=sum(1 for element in nodes if local_name(element.tag) == "chart"
                                       and "chart" in element.tag),
                            native_math=counts["oMath"], explicit_fonts=fonts,
                            combining_accents=combining, locks=sorted(set(locks)), review_flags=flags)
                report["slides"].append(info)
                report["review_flags"].extend(dict(slide=number, message=flag) for flag in flags)
    except (OSError, zipfile.BadZipFile, RuntimeError, ET.ParseError) as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
    report["status"] = "pass" if not errors else "error"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--expect-slides", type=int)
    parser.add_argument("--output", type=Path, help="Private JSON report; never the input PPTX")
    args = parser.parse_args()
    if args.expect_slides is not None and args.expect_slides < 1:
        parser.error("--expect-slides must be positive")
    if args.output and args.output.resolve() == args.pptx.resolve():
        parser.error("Output report cannot overwrite the input PPTX")
    report = inspect(args.pptx, args.expect_slides)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(f"{report['status']}: {report.get('slide_count', 0)} slides, "
              f"{len(report['errors'])} errors, {len(report['review_flags'])} review flags")
        for error in report["errors"]:
            print(error, file=sys.stderr)
    else:
        print(serialized)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
