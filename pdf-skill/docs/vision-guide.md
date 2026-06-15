# vision-guide — image-reading flow for scanned / chart-heavy PDFs

> How the model reads the **image** content of a PDF (scanned pages, charts,
> info-graphics, broken reading-order text) on this cloud sandbox. PDF
> read routes are split into:
>
> 1. **Text / table extraction** — default, see [`docs/read-guide.md`](read-guide.md) §3.1.
> 2. **Image reading** — this file. Two layers:
>    - `scripts/read_pdf_vision.py` renders the requested pages to PNGs.
>    - The **model** then reads each PNG itself, either via its native `read`
>      tool or via the single-image `matrix.image_understanding` MCP call.
> 3. **Coordinate-aware extraction, page count, decryption, rasterise** — see
>    [`docs/read-guide.md`](read-guide.md) §3–§4 inline cookbook recipes.
>
> There is no longer a "matrix vision MCP with stitched multi-page chunks" path
> inside the script. Stitching broke per-page fidelity (one upstream 502/413
> lost the whole chunk) and made it impossible to attribute values back to
> the right page. One PNG per page keeps the boundary explicit.

## Decision rule (model self-check)

For each rendered PNG in the manifest, the model uses **its own capability
to read the image** as the routing signal:

> - If the model can understand the image (it has vision / multimodal
>   capabilities AND the inline image fits in the model's image budget),
>   use the **native `read` tool**.
> - If the model cannot understand the image inline (text-only model, or
>   the page is too large for the model's inline image budget), use the
>   **`matrix.image_understanding` MCP** tool — it routes through a
>   separate vision model and returns the description as text.

The script marks oversized pages as `oversized: true` in the manifest as
a build-time size hint, but the **actual decision is the model's own at
call time** — try `read`, and if the model cannot process the image
inline, fall back to `image_understanding`. This mirrors the broader
"if you can read it, read; otherwise route through a specialist" pattern
in the cloud-runtime tool set.

## Why a render script at all

Even though the model can read PNGs on its own, the script exists to:

- **Render PDF pages to PNG** with the correct DPI / format. The model's
  `read` tool does not natively understand PDF.
- **Probe the PDF** with `pdfinfo` first (page count, encryption, corrupt
  detection) — the same double-safety net the rest of the read routes use.
- **Clamp `--pages`** to the actual page count and warn on out-of-range
  pages, instead of letting the model guess and re-render twice.
- **Cache rendered PNGs** in `~/.cache/mavis/pdf-render/<pdf-stem>/` so a
  re-run with the same `--pages` reuses the same files.
- **Flag oversized pages** (`> --oversized-bytes`) so the model knows
  to route them to `image_understanding` instead of the native `read`.

## Command

```bash
python3 -m scripts.read_pdf_vision --input file.pdf [opts]
```

Run from the `pdf` skill root (where `scripts/` lives) so the
`scripts` package is importable.

## Common parameters

| Argument | Purpose | Default |
|---|---|---|
| `--input <path>` | Path to the PDF (required) | — |
| `--pages <spec>` | Page range: `1-20` / `1,3,5` / `1-3,7,10-15` / `all`. Out-of-range pages are silently dropped with a stderr warning. | `all` |
| `--json` | Emit structured JSON manifest instead of Markdown | Markdown |
| `--max-stdout-bytes <n>` | Spill the manifest larger than `n` bytes to `~/.cache/mavis/pdf-out/<hash>.{md,json}` and return only a preview + path. `0` disables spilling. | `2048` |
| `--dpi <n>` | Render DPI per page | `150` |
| `--out-dir <path>` | Where to write the per-page PNGs. Default `~/.cache/mavis/pdf-render/<pdf-stem>/`. | content-addressed |
| `--oversized-bytes <n>` | Per-page byte threshold above which the manifest marks the page `oversized: true` and the model routes it to `image_understanding` MCP instead of native `read`. | `4000000` |

## How the model reads the rendered PNGs

The script's stdout is a manifest of rendered PNG paths. The model then
reads each one — it does NOT call the script's vision MCP itself.

**Step 1 — try native `read` on every page.** For each path in
`pages[].path`, call the `read` tool with the absolute path. The page
comes back as a multimodal input and the model can:

- transcribe the text in reading order (preserving paragraphs / lists / tables);
- describe any chart or info-graphic (axis labels, legend, series names,
  key values);
- detect a broken reading order (multi-column layouts where pdfplumber
  scrambled) and re-stitch the page mentally;
- OCR scanned-image pages that pdfplumber returned `(cid:NNN)` for.

The `read` tool is preferred because it avoids a network round-trip, keeps
per-page fidelity intact, and the model's response is a single coherent
turn.

**Step 2 — fall back to `matrix.image_understanding` for oversized pages.**
If a page is marked `oversized: true` in the manifest (or the model
otherwise cannot read the image inline), call the
`matrix.image_understanding` MCP tool with the same absolute path and a
short extraction prompt, e.g.:

```text
Transcribe every piece of text in this image in reading order. Preserve
paragraphs, lists, and tables. Briefly describe any charts.
```

`image_understanding` is a single-image call, not a stitched-chunk vision
pipeline, so per-page fidelity is preserved. One tool call per page — do
not batch pages together; the model loses the per-page boundary otherwise.

**Step 3 — never call `matrix.describe_images` from this flow.** The
matrix vision MCP's chunked multi-page route is not used by this skill
anymore. If you find yourself reaching for it, route through
`read_pdf_vision.py` → `read` / `image_understanding` instead.

## Time budget

| Page count | Render (1 thread) | Suggested caller timeout |
|---|---|---|
| 5 pages   | < 5 s    | 3 min (covers `read` model latency) |
| 10 pages  | ~5–10 s  | 5 min  |
| 30 pages  | ~15–30 s | 10 min |
| 100 pages | ~1 min   | 25 min |

The script itself finishes in seconds — pdfinfo probe + pdf2image render.
The dominant cost is the model's `read` / `image_understanding` call,
which is one tool call per page. For 100+ pages, batch the script with
`--pages 1-30`, `--pages 31-60`, etc., so the caller can also batch the
per-page reads.

## Error handling

| Error | Meaning | Action |
|---|---|---|
| `pdfinfo failed on <file>` (exit ≠ 0) | PDF corrupt or password-protected | Stop — pdfplumber / vision cannot recover |
| `'pdftoppm' not found` / `'pdf2image' not installed` | poppler / pip dep missing | Re-run image build; poppler is in `apt-get install poppler-utils` and pdf2image is in the runtime's pip list |
| Rendered PNG missing for a requested page | pdf2image silently skipped (rare) | Re-run with `--dpi 100` (lower memory) or split `--pages` |
| Native `read` returns "image too large" / blanks | page is too big for the model's image budget | The manifest already flagged it `oversized: true` — call `matrix.image_understanding` instead |
| `image_understanding` returns a transient error (`502`, `gemini analysis failed`) | upstream LLM hiccup | Retry the same tool call unchanged |
| `image_understanding` 401 / auth failed | matrix MCP token mismatch | Verify `MAVIS_ACCESS_TOKEN` + `MATRIX_BASE_URL` are paired; if not recoverable in this turn, fall back to `pdfplumber` text-only output and tell the user the visual content (charts / scans) could not be interpreted |

## Dependencies

```bash
pip3 install --user pdf2image pillow
brew install poppler        # pdftoppm (pdf2image backend) + pdfinfo
```

Both are baked into the cloud-compute runtime image — see
`packages/cloud-compute-runtime/Dockerfile` (apt) and the
`office-smoke.sh` probe list.

## Output spill (preventing context blow-up)

**Default:** when the manifest exceeds 2 KB, the script does NOT print the
full content to stdout. Instead it:

1. Writes the full content to `~/.cache/mavis/pdf-out/<sha256-prefix>.{md,json}`
   (named by content hash so identical outputs reuse the same file).
2. Returns the first 2 KB as a preview plus the absolute path on stdout.
3. Lets the model decide what to do next:
   - Read the whole file: `cat ~/.cache/mavis/pdf-out/abc...md`
   - Re-extract a narrower range: `python3 -m scripts.read_pdf_vision --input <file> --pages 14-18`

The rendered PNGs themselves live in
`~/.cache/mavis/pdf-render/<pdf-stem>/page_NNNN.png` and survive across
runs (content-addressed). To free disk, delete that directory.

**Markdown mode** prepends the preview with:

```markdown
<!-- mavis-pdf: output truncated, full text spilled to disk -->
> Full output: 12,345 bytes -> /Users/.../<hash>.md
> Showing first 2,048 bytes below.
> Read the file with `cat` / `grep`, or re-run with narrower `--pages`.
```

**JSON mode** wraps the spilled output:

```json
{
  "truncated": true,
  "totalBytes": 12345,
  "outputFile": "/Users/.../<hash>.json",
  "previewBytes": 2048,
  "preview": "..."
}
```

**Disable truncation** (full output to stdout): `--max-stdout-bytes 0`.
**Adjust threshold:** `--max-stdout-bytes 8192`, etc.

## JSON output schema

```jsonc
{
  "mode": "render",
  "file": "/abs/path.pdf",
  "pageCount": 18,
  "selectedPages": [1, 2, ..., 18],
  "dpi": 150,
  "outDir": "/Users/.../pdf-render/report",
  "pages": [
    {
      "page": 1,
      "path": "/Users/.../pdf-render/report/page_0001.png",
      "width": 1241,
      "height": 1754,
      "bytes": 1870055,
      "oversized": false
    },
    {
      "page": 2,
      "path": "/Users/.../pdf-render/report/page_0002.png",
      "width": 1241,
      "height": 1754,
      "bytes": 5200001,
      "oversized": true
    }
  ],
  "next": {
    "tool": "read",
    "fallbackTool": "matrix.image_understanding",
    "note": "For each `pages[].path`, call the native `read` tool. If a page is `oversized: true` (or the model otherwise cannot read the image inline), call `matrix.image_understanding` MCP with the same path and a short extraction prompt instead. Do not batch pages together."
  }
}
```

When truncated by `--max-stdout-bytes`, stdout returns the wrapper:

```jsonc
{
  "truncated": true,
  "totalBytes": 12345,
  "outputFile": "/Users/.../<hash>.json",
  "previewBytes": 2048,
  "preview": "..."   // first 2 KB of the full JSON above; trailing bytes may be invalid JSON
}
```

## Shared helper module

`scripts/_pdf_read_lib.py` — helpers used by `read_pdf_vision.py`:

- `parse_pages(raw)` / `validate_pages(pages, total)` / `format_pages(pages)`
- `maybe_spill_to_file(content, ext, max_bytes)`
- `add_common_args(parser)` / `emit(content, ext, max_bytes)`
- `resolve_input_or_exit(path)` / `resolve_pages_or_exit(raw, total)`
- `to_ranges(pages)` for pdf2image `first_page` / `last_page` batching
- `info(msg)` / `warn(msg)` / `die(msg)` for stderr progress

Kept under the original name `_pdf_read_lib.py` — the helpers are
read-side concerns (page spec parsing, output spill, stderr progress)
shared with any future cookbook helper script that needs them.
