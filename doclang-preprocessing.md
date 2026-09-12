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

## Where the HSA Receipts folder lives
`/Users/jesusgarcia/Library/CloudStorage/GoogleDrive-jesusleandra@gmail.com/My Drive/HSA Receipts`
(Google Drive, not local Documents).

## 2026-09-12 cleanup run (first run using doclang pre-processing)
Filed 1 new receipt (Creekside OB-GYN, Leandra, $121.70, 2026-06-30 — filed from a
billing statement, not a payment confirmation, so worth confirming it was actually paid),
paired 3 EOBs to receipts (2 to existing Lakeside Health rows, 1 to the new Creekside row).
9 EOBs left in `_Inbox` as needs-attention — each has no matching receipt/bill on file yet:
- 2026-06-23 & 2026-07-07 MyPremiseHealth (Jesus, $40 each, therapy) — two therapy visits
  with no filed receipt (only 07-21 has been filed so far).
- 2026-07-24 MRI (Jesus, Sukhraj Kahlon) — **$1,277.86 patient responsibility, no receipt on file.**
- 2026-07-29 imaging (Jesus, Paul Cripe, $10.94), 2026-08-12 imaging x2 (Jesus, Quireno
  Deguchy Jr $24.68 and Daniel Hofstedt $28.46), 2026-05-08 imaging x2 (Jesus, Jeffrey
  Heffernon, $148.89 and $147.01, same claim batch J0E1) — all no receipt on file.
- `EOB_jesus-selene_2026-07.pdf` — scanned family-summary EOB (period 6/16-7/07, total
  resp. $282.15), OCR too garbled to reliably extract line items; needs manual review.
  It also references a second claim on Leandra's `EOB_leandra_2026-07.pdf`
  (62309584-01, $189.27) with no receipt on file.

Unreimbursed total after this run: $3,219.23 (19 rows in tracker).
