#!/usr/bin/env python3
"""
Convert a PDF into a DocLang (.dclg) XML document (spec v0.7).

For text-layer PDFs: uses PyMuPDF's structured text extraction (blocks/lines/spans)
to build <heading>/<text> elements with normalized <location> bounding boxes.

For scanned/image-only PDFs (no extractable text layer): rasterizes each page and
runs Tesseract OCR, grouping OCR words into paragraphs by (block, par) index.

Coordinates are normalized to a document-wide default resolution of 1000x1000
(declared once in <head><default_resolution .../></head>), independent of each
page's actual point/pixel size.
"""
import sys
import statistics
from xml.sax.saxutils import escape

import fitz  # PyMuPDF

RESOLUTION = 1000


def norm(v, dim):
    v = max(0.0, min(float(dim), v))
    return max(0, min(RESOLUTION - 1, round(v / dim * RESOLUTION)))


def location_block(bbox, page_w, page_h):
    x0, y0, x1, y1 = bbox
    vals = [
        norm(x0, page_w),
        norm(y0, page_h),
        norm(x1, page_w),
        norm(y1, page_h),
    ]
    return "".join(f'<location value="{v}"/>' for v in vals)


def clean_text(s):
    # Collapse internal whitespace runs but keep line breaks meaningful.
    lines = [ln.strip() for ln in s.splitlines()]
    lines = [ln for ln in lines if ln != ""]
    return "\n".join(lines)


def extract_text_layer(doc):
    """Yield (page_index, elements) using the PDF's real text layer."""
    # First pass: gather all span sizes to find the "body" font size.
    sizes = []
    for page in doc:
        d = page.get_text("dict")
        for block in d["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        sizes.append(round(span["size"], 1))
    body_size = statistics.median(sizes) if sizes else 10.0

    for page in doc:
        page_w, page_h = page.rect.width, page.rect.height
        d = page.get_text("dict")
        elements = []
        for block in d["blocks"]:
            if block.get("type") != 0:
                continue  # skip images; picture support omitted for this pass
            bbox = block["bbox"]
            block_lines = []
            max_size = 0.0
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"])
                if line_text.strip():
                    block_lines.append(line_text)
                for span in line["spans"]:
                    max_size = max(max_size, span["size"])
            text = clean_text("\n".join(block_lines))
            if not text:
                continue
            is_heading = (
                max_size > body_size * 1.25
                and len(text) < 120
                and "\n" not in text
            )
            elements.append((is_heading, bbox, text))
        yield page_w, page_h, elements


def extract_ocr(doc, zoom=3.0):
    """Yield (page_w, page_h, elements) using Tesseract OCR for image-only pages."""
    import pytesseract
    from pytesseract import Output
    from PIL import Image
    import io

    for page in doc:
        page_w, page_h = page.rect.width, page.rect.height
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img_w, img_h = pix.width, pix.height
        data = pytesseract.image_to_data(img, output_type=Output.DICT)

        groups = {}
        n = len(data["text"])
        for i in range(n):
            word = data["text"][i].strip()
            if not word:
                continue
            key = (data["block_num"][i], data["par_num"][i])
            g = groups.setdefault(
                key, {"words": [], "x0": 1e9, "y0": 1e9, "x1": -1e9, "y1": -1e9}
            )
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            )
            g["words"].append((data["line_num"][i], word))
            g["x0"] = min(g["x0"], x)
            g["y0"] = min(g["y0"], y)
            g["x1"] = max(g["x1"], x + w)
            g["y1"] = max(g["y1"], y + h)

        elements = []
        for key in sorted(groups.keys()):
            g = groups[key]
            lines = {}
            for line_num, word in g["words"]:
                lines.setdefault(line_num, []).append(word)
            text = clean_text(
                "\n".join(" ".join(lines[ln]) for ln in sorted(lines.keys()))
            )
            if not text:
                continue
            # Scale pixel coords (rendered at `zoom`) back to page point space.
            bbox = (
                g["x0"] / img_w * page_w,
                g["y0"] / img_h * page_h,
                g["x1"] / img_w * page_w,
                g["y1"] / img_h * page_h,
            )
            elements.append((False, bbox, text))
        yield page_w, page_h, elements


def build_dclg(pages, source_name):
    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.7">')
    out.append(
        f'<head><default_resolution width="{RESOLUTION}" height="{RESOLUTION}"/>'
        f"<description>Converted from PDF: {escape(source_name)}</description>"
        f"</head>"
    )
    for i, (page_w, page_h, elements) in enumerate(pages):
        if i > 0:
            out.append("<page_break/>")
        for is_heading, bbox, text in elements:
            loc = location_block(bbox, page_w, page_h)
            tag = "heading" if is_heading else "text"
            out.append(f"<{tag}>{loc}{escape(text)}</{tag}>")
    out.append("</doclang>")
    return "\n".join(out)


def convert(pdf_path, out_path):
    doc = fitz.open(pdf_path)
    total_chars = sum(len(p.get_text()) for p in doc)
    if total_chars > 20:
        pages = list(extract_text_layer(doc))
        method = "text-layer"
    else:
        pages = list(extract_ocr(doc))
        method = "ocr"
    xml = build_dclg(pages, pdf_path.split("/")[-1])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    return method, sum(len(e) for _, _, e in pages)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    method, n = convert(src, dst)
    print(f"{dst}: method={method} elements={n}")
