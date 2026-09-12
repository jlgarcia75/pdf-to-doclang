# PDF → DocLang pre-processing for HSA inbox cleanup

Added a pre-processing step ahead of the `hsa-inbox-cleanup` skill: convert each PDF in
`_Inbox` to [DocLang](https://github.com/doclang-project/doclang) (`.dclg`, spec v0.7)
before extracting receipt/EOB fields, per the user's request.

## How it works
- `doclang` Python package (`pip install "doclang[schematron-saxon]"`) provides the CLI
  (`doclang validate`) and the real XSD/Schematron used to validate output.
- Converter script `pdf_to_doclang.py` (this file):
  - Text-layer PDFs: PyMuPDF `page.get_text("dict")` → blocks/lines/spans; heading vs.
    body text decided by font-size heuristic (>1.25x median body size, short, single line).
  - Scanned/image-only PDFs (no extractable text): render page to image, OCR with
    Tesseract (`pytesseract.image_to_data`), group words into paragraphs by
    (block_num, par_num).
  - Coordinates normalized to a document-wide 1000x1000 grid (`<head><default_resolution
    width="1000" height="1000"/></head>`), each `<location value="N"/>` clamped to
    `[0, 999]` (schema requires `0 <= value < axis_limit`, NOT `<=`).
  - Table detection via PyMuPDF's `find_tables()` was tried and abandoned — unreliable
    on these EOB layouts (garbled multi-line cells). Content is emitted as plain
    `<heading>`/`<text>` blocks in reading order instead.
- Validate every generated `.dclg` with `doclang validate` before use (XSD + Schematron).
- Requires: `pip install "doclang[schematron-saxon]" pymupdf pytesseract pillow`, plus
  the `tesseract` binary on PATH for OCR fallback.

## Usage
```
python3 pdf_to_doclang.py input.pdf output.dclg
```
