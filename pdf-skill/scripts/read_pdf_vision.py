#!/usr/bin/env python3
"""read_pdf_vision.py — render PDF pages to PNGs for native / `image_understanding` reading.

Renders selected pages with pdf2image (poppler) to a temp directory, one PNG
per page, and emits a structured manifest of the rendered file paths. The
caller (the model) then reads each PNG itself:

  1. First try the native `read` tool on the PNG path. The model receives the
     page inline as a multimodal input, and can extract text / describe
     charts / read scanned-image PDFs directly. This is the preferred path
     for any single page that fits in the model's image budget.

  2. If a single page is too large (or the model otherwise cannot read it
     inline), fall back to the matrix `image_understanding` MCP tool with
     the PNG path. `image_understanding` is a single-image call, not a
     stitched-chunk vision pipeline, so it preserves per-page fidelity.

The script intentionally does NOT call any vision MCP itself. Stitched
multi-page chunking (the previous behaviour) is removed: it produced
chunks where a 502 / 413 upstream rejection would lose the whole chunk,
and the model could no longer attribute values to specific pages. One PNG
per page keeps the per-page boundary explicit and matches how the
`read` / `image_understanding` tools receive images.

This is the only wrapped read script in pdf: rendering pages needs
poppler + pdf2image, which is too much plumbing for a cookbook recipe.
Other read scenarios (text / tables / coordinates / raster / decrypt /
metadata) live as inline recipes in docs/read-guide.md.

Usage (run from the pdf skill root):
    python3 -m scripts.read_pdf_vision --input file.pdf [--pages 1-20]
                                       [--dpi 150] [--out-dir DIR]
                                       [--json] [--max-stdout-bytes N]

Dependencies (all `pip3 install --user`):
  - pdf2image (also needs poppler / `brew install poppler` for the
    pdftoppm backend)
  - Pillow
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts._pdf_read_lib import (
    add_common_args,
    cache_dir,
    die,
    emit,
    format_pages,
    info,
    resolve_input_or_exit,
    resolve_pages_or_exit,
    to_ranges,
    warn,
)

try:
    from pdf2image import convert_from_path  # type: ignore
except ImportError:
    die("pdf2image not installed. Install: pip3 install --user pdf2image (and brew install poppler)")

try:
    from PIL import Image  # type: ignore
except ImportError:
    die("Pillow not installed. Install: pip3 install --user pillow")

DEFAULT_DPI = 150
# Soft advisory only — pages larger than this are still rendered, but the
# emitted manifest flags them with `oversized: true` so the model can decide
# to skip the native `read` and route to `image_understanding` MCP.
DEFAULT_OVERSIZED_BYTES = 4_000_000


def _safe_tmp_root() -> Path:
    env_tmp = os.environ.get("TMPDIR", "")
    if env_tmp and not env_tmp.startswith("/tmp"):
        return Path(env_tmp)
    return cache_dir().parent  # ~/.cache/mavis/


# CLOUD-OVERLAY: cloud sandbox version. Base at
#   packages/daemon/skills/pdf/scripts/read_pdf_vision.py
#
# 2026-06 refactor: this script used to POST stitched multi-page chunks to
# the matrix `describe_images` MCP (see git history `3fd8102ac^` for the
# last MCP-vision version). The new flow renders one PNG per page and
# returns the file paths so the model can use its native `read` tool (or
# the single-image `image_understanding` MCP) directly. See
# `docs/vision-guide.md` §`read_pdf_vision.py` for the rationale.


def _probe_page_count(pdf: Path) -> int:
    """Run pdfinfo once up front — page count + corruption safety net."""
    if shutil.which("pdfinfo") is None:
        die("'pdfinfo' (poppler) not found. Install: brew install poppler")
    try:
        out = subprocess.check_output(
            ["pdfinfo", str(pdf)], stderr=subprocess.STDOUT
        ).decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError as e:
        err_tail = (e.output or b"").decode("utf-8", errors="ignore").strip()[-300:]
        die(
            f"pdfinfo failed on {pdf} (exit {e.returncode}). "
            f"PDF may be corrupt or password-protected. pdfinfo said: {err_tail}"
        )
    total = next(
        (int(line.split(":", 1)[1].strip()) for line in out.splitlines() if line.startswith("Pages:")),
        0,
    )
    if total == 0:
        die(f"Could not determine page count for {pdf} (pdfinfo output had no 'Pages:' line)")
    return total


def _render(pdf: Path, pages: list[int], dpi: int, out_dir: Path) -> list[dict]:
    """Render each selected page to its own PNG inside `out_dir`.

    Returns a list of {page, path, width, height, bytes, oversized} dicts,
    one per requested page, in page order.
    """
    if shutil.which("pdftoppm") is None:
        die("'pdftoppm' (poppler) not found. Install: brew install poppler")

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict] = []
    for lo, hi in to_ranges(pages):
        # pdf2image numbers from `first_page`; results length == hi - lo + 1
        imgs = convert_from_path(
            str(pdf),
            dpi=dpi,
            first_page=lo,
            last_page=hi,
            fmt="png",
            output_folder=str(out_dir),
            paths_only=False,
        )
        for i, img in enumerate(imgs):
            page_num = lo + i
            target = out_dir / f"page_{page_num:04d}.png"
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            target.write_bytes(data)
            rendered.append(
                {
                    "page": page_num,
                    "path": str(target),
                    "width": img.width,
                    "height": img.height,
                    "bytes": len(data),
                    "oversized": len(data) > DEFAULT_OVERSIZED_BYTES,
                }
            )
    return rendered


def _default_out_dir(pdf: Path) -> Path:
    """Choose a stable, content-addressed output directory so re-runs of
    the same PDF / page set reuse the same PNGs (avoids re-rendering)."""
    cache = cache_dir().parent / "pdf-render"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / pdf.stem


def main() -> None:
    p = argparse.ArgumentParser(
        description="Render PDF pages to PNGs for native read / image_understanding.",
    )
    add_common_args(p)
    p.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI, help=f"Render DPI (default {DEFAULT_DPI})."
    )
    p.add_argument(
        "--out-dir",
        default=None,
        help=(
            "Directory to write the per-page PNGs into. Default: "
            "~/.cache/mavis/pdf-render/<pdf-stem>/ — content-addressed, "
            "so re-runs reuse the same PNGs."
        ),
    )
    p.add_argument(
        "--oversized-bytes",
        type=int,
        default=DEFAULT_OVERSIZED_BYTES,
        help=(
            f"Flag any rendered PNG larger than this as `oversized: true` in "
            f"the manifest so the model routes it to `image_understanding` "
            f"instead of native `read`. Default {DEFAULT_OVERSIZED_BYTES}."
        ),
    )
    args = p.parse_args()

    pdf_path = resolve_input_or_exit(args.input)
    total_pages = _probe_page_count(pdf_path)
    info(f"PDF probe: {total_pages} page(s) total")
    selected = resolve_pages_or_exit(args.pages, total_pages)

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else _default_out_dir(pdf_path)
    info(f"Rendering {len(selected)} page(s) at {args.dpi} DPI → {out_dir}")
    rendered = _render(pdf_path, selected, args.dpi, out_dir)
    oversized = [r for r in rendered if r["oversized"]]
    if oversized:
        warn(
            f"{len(oversized)} page(s) larger than {args.oversized_bytes} bytes — "
            f"the manifest marks them `oversized: true`; route those to "
            f"`image_understanding` MCP instead of native `read`."
        )

    manifest = {
        "mode": "render",
        "file": str(pdf_path),
        "pageCount": total_pages,
        "selectedPages": selected,
        "dpi": args.dpi,
        "outDir": str(out_dir),
        "pages": rendered,
        "next": {
            "tool": "read",
            "fallbackTool": "matrix.image_understanding",
            "note": (
                "For each `pages[].path`, call the native `read` tool. If a page is "
                "`oversized: true` (or the model otherwise cannot read the image "
                "inline), call `matrix.image_understanding` MCP with the same path "
                "and a short extraction prompt instead. Do not batch pages together."
            ),
        },
    }

    if args.json:
        emit(
            __import__("json").dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            "json",
            args.max_stdout_bytes,
        )
        return

    sel_spec = format_pages(selected)
    lines: list[str] = [
        f"# {pdf_path.name}",
        "",
        f"> {total_pages} pages • selected {sel_spec} • {len(rendered)} PNG(s) @ {args.dpi} DPI",
        f"> output dir: {out_dir}",
        "",
        "## Next step for the model",
        "",
        "For each PNG path below, call the native `read` tool. If a page is marked",
        "`oversized: true` (or the model cannot read the image inline), call the",
        "`matrix.image_understanding` MCP tool with the same path and a short",
        "extraction prompt. Do not batch pages together — one tool call per page.",
        "",
        "## Rendered pages",
        "",
    ]
    for r in rendered:
        flag = " ⚠ oversized" if r["oversized"] else ""
        lines.append(
            f"- page {r['page']}: `{r['path']}` "
            f"({r['width']}×{r['height']}, {r['bytes']} bytes){flag}"
        )
    emit("\n".join(lines) + "\n", "md", args.max_stdout_bytes)


if __name__ == "__main__":
    main()
