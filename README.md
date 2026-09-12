# PDF → DocLang

A small Python utility that converts a PDF into a DocLang XML document (`.dclg`) for downstream document extraction workflows such as HSA inbox cleanup.

The converter supports two extraction modes:

- A text-layer PDF path that reads structured page text from PyMuPDF and emits DocLang `heading` and `text` elements.
- An OCR fallback path for scanned or image-only PDFs that rasterizes the page and uses Tesseract to recover paragraphs from the image.

The repository is intentionally lightweight and designed around a simple CLI workflow.

## Repository contents

- `pdf_to_doclang.py` — main converter script
- `doclang-preprocessing.md` — implementation notes and preprocessing design rationale

## Features

- Converts PDFs into DocLang v0.7 XML
- Normalizes page coordinates into a document-wide `1000 x 1000` coordinate grid
- Emits headings when text appears visually prominent or structurally heading-like
- Falls back to OCR for scanned PDFs
- Produces XML compatible with DocLang validation tooling

## Requirements

Install the Python dependencies:

```bash
pip install "doclang[schematron-saxon]" pymupdf pytesseract pillow
```

You also need the Tesseract binary available on your `PATH` for the OCR fallback.

## Usage

```bash
python3 pdf_to_doclang.py input.pdf output.dclg
```

Example:

```bash
python3 pdf_to_doclang.py ./samples/invoice.pdf ./samples/invoice.dclg
```

The generated `.dclg` file is a valid DocLang document with a `head` element that declares the default resolution, followed by structured `heading` and `text` nodes.

## Conversion workflow

1. Run the converter on a PDF.
2. Validate the generated `.dclg` file with DocLang tooling:

```bash
doclang validate output.dclg
```

3. Feed the validated DocLang file into the document extraction or inbox-cleanup pipeline.

## Notes

The repository uses PDF text extraction on pages that contain an extractable text layer. When no meaningful text layer is found, the script switches to OCR by rendering the page and grouping Tesseract word output into paragraph-level blocks.

The repository documentation also records that table detection was attempted but ultimately abandoned because the PDF layouts produced unreliable extraction results. The converter therefore emits plain document-order text and heading blocks instead of tabular structure.

## License

This repository does not currently declare a specific license file. Add an appropriate open-source license if you intend to publish or reuse the project publicly.
