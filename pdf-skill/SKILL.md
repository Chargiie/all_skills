---
name: pdf
description: >
  Unified PDF skill — generate, reformat, fill, and read PDFs. Covers: text-to-PDF (reports, resumes, proposals, 可视化报告), Markdown→PDF conversion, PDF form filling, and PDF reading/extraction/OCR.
  Trigger on any task with PDF as primary input or output. Not for DOCX or PPT.
metadata:
  version: '3.0-cloud'
  category: document-pdf
---

# pdf

Unified PDF skill. The model chooses the route based on user intent; this SKILL.md is an index. Each
route has its own guide in `docs/`. Read the guide before authoring or running anything.

## Operational rules — read before doing anything

> **0. Cloud sandbox: LaTeX IS available — `xelatex` / `latexmk` from TeX Live.** This build ships
> `texlive-xetex` + `texlive-latex-recommended` + `texlive-lang-chinese` + `texlive-fonts-recommended`
> (apt fallback path (b) per the Dockerfile §Tectonic comment; ~1.5 GB on disk). The
> `LATEX_THESIS` and `LATEX_TECHNICAL_BOOK` routes are now active: invoke
> `xelatex` / `latexmk -xelatex` directly, or use the templates under
> `templates/latex-academic-thesis/` and `templates/latex-technical-book/` whose READMEs
> already encode the right command for this toolchain. `tectonic` itself is still NOT
> installed (no reachable GitHub release mirror from the buildkit cluster); the guides
> recommend `xelatex` / `latexmk` as the active path and `tectonic` only as a "if you
> migrate to path (a)" future option.

> **1. Match user query against [`docs/pitfalls-index.md`](docs/pitfalls-index.md) FIRST.** It
> contains 10 production-ready **canonical query templates** (P1–P10), each with a
> `Match signatures` block (sample queries) and a complete executable prompt that already encodes
> every known pitfall, verification gate, and fall-back path. Workflow:
>
> 1. Scan the Quick lookup table — match user's query keywords to a row.
> 2. **Copy the matching canonical query verbatim**, substitute the `Slots` (e.g. `{PDF_PATH}`,
>    `{OUTPUT_PATH}`) with the user's actual values, and execute step-by-step.
> 3. Multiple partial matches → fuse: take the strictest verification from each, never relax a
>    constraint.
> 4. No match → fall back to the Routes / route guides below.
>
> Skip any P-case whose route table maps to LATEX_THESIS / LATEX_TECHNICAL_BOOK — those tools
> are not in this sandbox; substitute CREATE (HTML→PDF) with the academic typography preset.
>
> Do NOT skip verification steps in the canonical queries — they exist because past evaluation runs
> shipped wrong outputs without them.

> **2. Locate before bulk-extracting any non-trivial PDF.** Three independent thresholds, all
> enforced together:
>
> | Threshold                                                              | Rule                                                                                                                                            |
> | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
> | **>20 pages** AND user wants a specific datum (not the whole document) | locate-first is **mandatory** — do not run pdfplumber over every page; build a heading index first (pypdf outline → printed TOC → keyword grep) |
> | **2 blind grep passes** without landing on the target                  | stop and build the heading index, regardless of page count — a 3rd / 4th / 5th keyword search is the most common time sink                      |
> | **>200 pages**                                                         | always build a heading index up-front, even before the first grep — at this size 6-8 blind greps balloon into 30+ shell calls                   |
>
> See [`docs/read-guide.md`](docs/read-guide.md) §3 for the actual outline / TOC / grep recipes.

> **3. Chart pages and complex financial tables — vision, ONE PAGE PER CALL, mandatory.** Any page
> with a chart / diagram / info-graphic whose values matter, **or** any page with a complex
> financial / regulatory table (balance sheet, income statement, cash-flow, debt schedule —
> multi-level headers, merged cells, footnoted sub-totals), MUST go through `read_pdf_vision.py` AND
> be invoked with `--pages N` (a single page, never a range). pdfplumber returns scrambled fragments
> on these layouts even when the PDF is text-native. After the script renders each page to a PNG,
> the model reads the page itself — first with the native `read` tool, falling back to
> `matrix.image_understanding` MCP for any page flagged `oversized: true` in the manifest. Never
> batch pages together: one tool call per page so per-page fidelity is preserved and the model can
> attribute values back to the correct page.

> **4. Verify HTML→PDF page size and chart presence after every render.** Always pass `--format A4`
> or `--format Letter` explicitly to `make.sh render` — Chromium overrides CSS `@page { size }` when
> the CLI flag is missing. After render:
>
> ```bash
> pdfinfo out.pdf | grep "Page size"        # must match user intent
> pdfimages -list out.pdf | tail -n +3 | wc -l   # ≥ 1 per chart / logo
> ```
>
> `pdftotext` cannot see images and will silently pass a chart-less deck. Both checks are mandatory.

> **5. Don't suppress stderr.** `2>/dev/null` is **never** the right choice in this skill
> (`make.sh render`/`reformat`/`fill`, `read_pdf_vision.py`, `pdfinfo`, `pdftotext`, `pdfimages`,
> `qpdf`). On failure you lose the only signal that explains why and have to rerun blind. If output
> is too noisy, redirect to a log file and grep on demand:
>
> ```bash
> python3 -m scripts.read_pdf_vision --input report.pdf --pages 5 \
>   2>/tmp/vision.log
> # If the result looks wrong, only then:
> #   grep -in "error\|trace\|fail" /tmp/vision.log | head -20
> ```

> **6. Always serialise JSON with `ensure_ascii=False`.** When this skill writes a JSON config /
> manifest that a downstream step parses (chart data, content manifests, form values), use
> `json.dumps`, never hand-concatenate strings. CJK / smart quotes / em-dashes in data are the most
> common reason a "looks fine" JSON file fails to `json.load()`:
>
> ```python
> Path("content.json").write_text(
>     json.dumps(payload, ensure_ascii=False, indent=2),
>     encoding="utf-8",
> )
> ```

> **7. AcroForm fill — copy the one canonical pypdf snippet.** In pypdf ≥ 4 the only working pattern
> is `PdfWriter(clone_from=src)` + `update_page_form_field_values(...)`
>
> - `set_need_appearances_writer(True)`. `clone_reader_document_root`, direct `/Annots` patching,
>   and `append_pages_from_reader` all _silently_ produce a PDF with no values written — there is no
>   error to debug. See [`docs/forms-guide.md`](docs/forms-guide.md) §B.

> **8. Header/footer discipline for generated PDFs.** For any formal or multi-page PDF (contracts,
> reports, proposals, forms, manuals, translated documents), decide the header/footer strategy
> before rendering: preserve source headers/footers when present; otherwise add a conservative
> running header/footer or explicitly justify why none is appropriate (e.g. cover-only one-pager).
> Reserve print-space so running elements do not collide with body content, tables, signatures, or
> charts. Verification must include a visual check of at least one body page and the
> final/signature/table-heavy page, not only `pdftotext`. Implementation details live in
> [`docs/html-pdf-spec.md`](docs/html-pdf-spec.md) §3.3.

> **9. DOCX→PDF is a DOCX-native render/export task, not an HTML task.** When the user asks to
> convert a Word/DOCX file to PDF while preserving the Word document, route to `docx` / the
> DOCX renderer first (e.g. `scripts/docx_to_pdf.py` or LibreOffice/soffice export). DOCX already
> has native page geometry, styles, sections, headers/footers, fields, numbering, and table layout;
> converting DOCX → Markdown/HTML → PDF just to make a PDF is a fidelity bug. Verify the native PDF
> with `pdfinfo`, `pdftotext`, and visual spot checks. Use HTML→PDF only for explicit
> redesign/recomposition, when the native render is visibly unacceptable, or when the requested
> deliverable is a newly authored web/print design. If HTML is used, say it is a recomposition
> route, not the default DOCX→PDF conversion path.

> **10. Every PDF output needs clickable TOC/index navigation, regardless of route.** This is a
> global delivery contract for CREATE, REFORMAT, FILL/overlay, MUTATE/merge/split, DOCX-native
> export handoff, and any read→write chain. Any multi-page PDF produced, transformed, merged, or
> substantially reformatted by this skill must include a visible TOC / index that maps major
> sections to their destination pages and is clickable in the final PDF. For HTML→PDF, implement
> TOC rows as internal anchors (`<a href="#section-id">`) and give every target section a stable,
> unique `id`. For markdown/text reformatting, generate or preserve a TOC before rendering; do not
> ship a flat prose PDF without navigable section links. For filled forms, official one-page forms
> may omit TOC, but multi-page filled packets must preserve existing bookmarks/links or add an
> index/outline without altering the form semantics. For merged/split/watermarked/pypdf/reportlab-built
> outputs, preserve existing links where possible and add/update PDF outline/bookmarks plus
> `/Link` annotations when the visible TOC cannot be generated by the renderer alone. Exceptions are
> only single-page forms/posters/certificates or source-faithful official forms where adding
> pages/visual TOC would invalidate the document; the delivery note must explicitly say why and
> what navigation was preserved instead. Verification must include checking link or outline
> annotations and spot-clicking several TOC/index entries to confirm they land on the intended
> pages.

## Routes — pick by user intent, then read the guide

### WRITE a PDF

| Intent                                                                                                                                                              | Guide                                                                                                                                                               | Entry                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **CREATE** — author a polished PDF from scratch (cover, charts, KPI grids, branded report)                                                                         | [`docs/create-guide.md`](docs/create-guide.md) + [`docs/design-guide.md`](docs/design-guide.md) + [`templates/INDEX.md`](templates/INDEX.md)                        | `bash scripts/make.sh render --in page.html --out out.pdf`   |
| **LATEX_THESIS** — academic thesis / dissertation authored in LaTeX, compiled with xelatex + bibtex                                                                | [`docs/latex-academic-thesis-guide.md`](docs/latex-academic-thesis-guide.md) + [`templates/latex-academic-thesis/`](templates/latex-academic-thesis/)              | `xelatex main.tex && bibtex main && xelatex main.tex && xelatex main.tex` |
| **LATEX_TECHNICAL_BOOK** — engineering monograph / technical book authored in LaTeX, compiled with latexmk -xelatex                                                | [`docs/latex-technical-book-guide.md`](docs/latex-technical-book-guide.md) + [`templates/latex-technical-book/`](templates/latex-technical-book/)                  | `latexmk -xelatex -interaction=nonstopmode main.tex`          |
| **REFORMAT** — restyle markdown / text / pdf as a clean PDF (no charts, no design recomposition)                                                                    | [`docs/reformat-guide.md`](docs/reformat-guide.md)                                                                                                                  | `bash scripts/make.sh reformat --input src.md --out out.pdf` |
| **FILL** — write values into a PDF form (AcroForm or visual overlay)                                                                                                | [`docs/forms-guide.md`](docs/forms-guide.md)                                                                                                                        | `bash scripts/make.sh fill probe form.pdf`                   |
| **MUTATE** — merge / split / rotate / crop / watermark / encrypt / annotate / sign / replace text                                                                   | [`docs/advanced-reference.md`](docs/advanced-reference.md)                                                                                                          | qpdf / pypdf / reportlab cookbook (no in-skill route)        |

> Mechanical contract for any HTML→PDF authoring (page geometry, page-break rules, Chart.js settle,
> CJK cascade, color fidelity) lives in [`docs/html-pdf-spec.md`](docs/html-pdf-spec.md). Read it
> before writing any new HTML.
>
> The LaTeX templates under `templates/latex-academic-thesis/` and `templates/latex-technical-book/`
> compile with `xelatex` / `latexmk -xelatex` (TeX Live, baked into the image). `tectonic` is
> preferred upstream for its single-binary ergonomics but is not installed in this image — the
> Dockerfile §Tectonic comment documents the rationale.

### READ a PDF

| Intent                                                                                | Guide                                            | Entry                                                                |
| ------------------------------------------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------- |
| **Default** — text + tables from any text-native PDF                                  | [`docs/read-guide.md`](docs/read-guide.md) §3.1  | `pdfplumber` (5–10 line inline recipe)                               |
| **Image reading** — scanned / image-only PDFs, chart values, broken reading order     | [`docs/vision-guide.md`](docs/vision-guide.md)   | `python3 -m scripts.read_pdf_vision --input report.pdf --pages 1-30`, then native `read` / `image_understanding` MCP per page |
| Coordinate-aware extraction, page count, decryption, rasterise pages                  | [`docs/read-guide.md`](docs/read-guide.md) §3–§4 | inline cookbook recipes                                              |

> Default to **pdfplumber**. Only escalate to image reading when the text path is insufficient
> (`(cid:NNN)` glyphs, empty strings, charts that matter, magazine-style layout). Image reading in
> cloud sandbox is a two-step flow: `read_pdf_vision.py` renders each selected page to its own
> PNG, then the model reads each PNG itself (native `read` first, `matrix.image_understanding`
> MCP for any page flagged `oversized: true` in the manifest). The script does NOT call the vision
> MCP itself — one PNG per page keeps per-page fidelity intact. Details:
> [`docs/vision-guide.md`](docs/vision-guide.md).

### Combined chains — read then write

When the source is an existing PDF, run the read route first, then feed the extracted text/markdown
into REFORMAT or CREATE. Common patterns:

| User intent                           | Read step                                                                                                                     | Write step                                                                                                                                                                                                                |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Restyle an existing PDF               | pdfplumber recipe ([`docs/read-guide.md`](docs/read-guide.md) §3.1) for text-native, or `read_pdf_vision.py` for layout-heavy | REFORMAT — pass extracted markdown as `--input`                                                                                                                                                                           |
| Fill an unfamiliar form               | `read_pdf_vision.py` to describe field layout/labels                                                                          | `bash scripts/make.sh fill probe`, then [`docs/forms-guide.md`](docs/forms-guide.md)                                                                                                                                      |
| Author a PDF inspired by a reference  | `read_pdf_vision.py` on the reference (palette, cover, sections)                                                              | CREATE — encode cues in HTML (CSS variables + cover archetype)                                                                                                                                                            |
| Translate a PDF/EML preserving layout | EML: parse text/html + cid assets; PDF: pdfplumber per page (or vision if scanned / broken layout)                            | REFORMAT + [`templates/translate-preserve-layout/`](templates/translate-preserve-layout/); for rich EML load [`docs/email-translation-goldman-two-sessions-case.md`](docs/email-translation-goldman-two-sessions-case.md) |
| Verify a generated PDF (sanity loop)  | pdfplumber on the freshly written file                                                                                        | n/a — write → read                                                                                                                                                                                                        |

## Out of scope

- OCR a single image with no PDF involved → call the model's native `read` tool (or
  `matrix.image_understanding` MCP for oversized images) directly.
- Desktop-grade PDF editing (paragraph reflow, font substitution) → not an automation job.
- `.docx` or `.pptx` → use `docx` / `pptx`.
- Authoring long-form thesis / book **content** from scratch → for academic / book PDFs use the
  LATEX_THESIS / LATEX_TECHNICAL_BOOK routes; the skill provides the compile toolchain and
  template skeletons only, do not generate full body text without user-provided source material.

## Reference index

| File                                                                                                                               | Purpose                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`docs/pitfalls-index.md`](docs/pitfalls-index.md)                                                                                 | **Read first when the task matches a known case.** 10 evaluation cases keyed by task signature → past failure → recommended trace                                                     |
| [`docs/create-guide.md`](docs/create-guide.md)                                                                                     | CREATE route: 4-step flow, component primitive cookbook, cover archetype re-skinning, verification checklist                                                                          |
| [`docs/markdown-static-academic-data-viz-case.md`](docs/markdown-static-academic-data-viz-case.md)                                 | P3 progressive case: Markdown report → A4 print-academic PDF, preserve source hierarchy, generate Matplotlib static charts for source tables, verify images/text/no Markdown remnants |
| [`docs/email-translation-goldman-two-sessions-case.md`](docs/email-translation-goldman-two-sessions-case.md)                       | P5 progressive case: rich EML research report → Chinese A4 PDF, optimized translation prompt, cid image preservation, link/image verification evidence                                |
| [`docs/ai-voice-cloning-regulatory-report-case.md`](docs/ai-voice-cloning-regulatory-report-case.md)                               | P4 progressive case: AI voice cloning multi-jurisdiction regulatory survey → Chinese A4 PDF, bilingual research prompts, fact-check report, optimized print-academic HTML source      |
| [`docs/reformat-guide.md`](docs/reformat-guide.md)                                                                                 | REFORMAT route: input formats, title-lift, accent re-skinning, "when NOT to REFORMAT"                                                                                                 |
| [`docs/forms-guide.md`](docs/forms-guide.md)                                                                                       | FILL route: probe → AcroForm or visual overlay, JSON schemas, geometry lint                                                                                                           |
| [`docs/read-guide.md`](docs/read-guide.md)                                                                                         | READ route: pdfplumber default, library + CLI cookbook, troubleshooting                                                                                                               |
| [`docs/vision-guide.md`](docs/vision-guide.md)                                                                                     | Image-reading flow: `read_pdf_vision.py` renders pages to PNGs, the model reads each PNG itself (native `read` / `image_understanding` MCP) — flags, JSON schema, time budget, error matrix |
| [`docs/html-pdf-spec.md`](docs/html-pdf-spec.md)                                                                                   | HTML→PDF mechanical contract — page geometry, page-break, Chart.js settle, CJK, color fidelity, quality gate                                                                          |
| [`../xlsx/docs/superstore-multiformat-conversion-case.md`](../xlsx/docs/superstore-multiformat-conversion-case.md)                 | Cross-skill X8/P9 case: 10k-row Superstore Excel → CSV/JSON/HTML→PDF + XML-template CSV→XLSX                                                                                          |
| [`docs/design-guide.md`](docs/design-guide.md)                                                                                     | Aesthetic layer — palette mood table, typography pairs, cover archetypes (incl. academic / book), anti-patterns                                                                       |
| [`docs/advanced-reference.md`](docs/advanced-reference.md)                                                                         | Mutation / annotation / signature / text replacement cookbook (qpdf, pypdf, reportlab)                                                                                                |
| [`docs/troubleshooting.md`](docs/troubleshooting.md)                                                                               | Environment / CJK / merge / verification / stale-script / read-side issues                                                                                                            |
| [`templates/INDEX.md`](templates/INDEX.md)                                                                                         | Templates index — eight skeletons (LaTeX scaffolds shipped but not compilable in cloud sandbox)                                                                                       |

## Environment

> **Cloud sandbox**: dependencies are baked into the image. `bash scripts/make.sh check` will probe
> the toolchain; xelatex / latexmk / pdflatex / bibtex should all report green (TeX Live
> installed — see Operational rule 0), all other tools should also report green. `tectonic` itself
> will emit a `WARN` — it's the upstream-preferred LaTeX binary but isn't installable in this
> build (see Dockerfile §Tectonic for the rationale and the path-(a) future). `bash scripts/make.sh
> fix` is a no-op in cloud sandbox (image is read-only-ish; `cmd_fix` short-circuits to
> `cmd_check`).

```bash
bash scripts/make.sh check        # verify CREATE / REFORMAT / FILL / READ / LATEX deps
```

`check` enforces minimum versions (Python ≥ 3.9, Node ≥ 18, pypdf ≥ 3.0, markdown-it-py ≥ 3.0) and
prints the actual installed version for each.

| Tool                                          | Used by                        | Status in cloud sandbox |
| --------------------------------------------- | ------------------------------ | ----------------------- |
| Python 3.9+                                   | all `.py` scripts              | ✅ baked in              |
| `markdown-it-py`                              | REFORMAT (`reformat_parse.py`) | ✅ baked in              |
| `pypdf`                                       | FILL, MUTATE                   | ✅ baked in              |
| `pdfplumber`                                  | READ (default)                 | ✅ baked in              |
| `pdf2image`, `pillow`, `pypdfium2`            | READ image reading + page rasterise | ✅ baked in              |
| Node.js 18+ + Chromium (Playwright)           | `render_html.cjs`              | ✅ baked in              |
| `pdfinfo`, `pdftotext`, `pdfimages` (poppler) | READ + verification            | ✅ baked in              |
| `qpdf`                                        | MUTATE / decryption            | ✅ baked in              |
| `xelatex` / `latexmk` / `pdflatex` / `bibtex` (TeX Live) | LATEX_THESIS / LATEX_TECHNICAL_BOOK | ✅ baked in (apt `texlive-xetex texlive-latex-recommended texlive-lang-chinese texlive-fonts-recommended`) |
| `tectonic`                                    | LATEX_THESIS / LATEX_TECHNICAL_BOOK | ❌ **not shipped** — `xelatex` / `latexmk` from TeX Live is the active compile chain (Dockerfile §Tectonic) |

`read_pdf_vision.py` in cloud sandbox renders the requested pages to per-page PNGs in
`~/.cache/mavis/pdf-render/<pdf-stem>/`; the model then reads each PNG itself (native `read` first,
`matrix.image_understanding` MCP for `oversized: true` pages). No vision MCP is called from inside
the script. Details: [`docs/vision-guide.md`](docs/vision-guide.md).
