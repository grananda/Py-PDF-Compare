---
name: pdf-compare
description: Compare two PDF files and produce a side-by-side visual diff report using this project. Use when the user asks to compare two PDFs, see what changed between two versions of a document, generate a PDF diff or difference report, or check whether two PDFs are identical. Also on phrasings like "compare these two PDFs", "what changed between these versions", "diff these documents".
---

# pdf-compare

Produces a PDF report with both documents side by side, page by page: deletions highlighted in red on the left, additions in green on the right, and inserted or deleted pages detected and labelled.

## 1. Resolve which build to run

Never invoke a bare `pdf-compare`. Resolve the source explicitly, stopping at the first candidate that validates:

```bash
REPO=""
for candidate in "$PDF_COMPARE_REPO" "$(git rev-parse --show-toplevel 2>/dev/null)"; do
  if [ -n "$candidate" ] && grep -qs '^name = "py-pdf-compare"' "$candidate/pyproject.toml"; then
    REPO="$candidate"; break
  fi
done
```

Checking `pyproject.toml` is not decorative: it prevents running an unrelated directory that happens to sit at the same path.

**With a working copy** (`$REPO` set) — runs your current source, so unpublished changes are exercised:

```bash
uv run --project "$REPO" pdf-compare <original.pdf> <modified.pdf> -o <report.pdf>
```

**Without one** — runs the published release, cloning and installing nothing:

```bash
uvx --from "py-pdf-compare@latest" pdf-compare <original.pdf> <modified.pdf> -o <report.pdf>
```

Both details of that command are load-bearing, and dropping either one breaks the result silently:

- **`--from`**, because the executable (`pdf-compare`) is not named after the distribution (`py-pdf-compare`).
- **`@latest`**, because uv caches the package index. Without it, uv can resolve an older release it already has cached even though a newer one is on PyPI — this has happened in practice, silently running a build from before the page alignment fixes.

> **Never run a bare `pdf-compare`.** A copy installed with `uv tool install` is frozen at whatever version was current that day and never updates itself. It can be far older than both the working copy and PyPI, and it produces wrong results without any warning that it is out of date.

## 2. Always state which build you ran

Report the source before the results. Without it, an odd result is indistinguishable from a stale binary — which is exactly how this ends up costing an hour.

- **Working copy**: path, branch and short SHA.

  ```bash
  git -C "$REPO" branch --show-current; git -C "$REPO" rev-parse --short HEAD
  ```

  If the branch is not `main`, or there are uncommitted changes, **say so**: the comparison ran against code nobody else can reproduce.

- **Published release**: say it came from PyPI, and which version uv resolved.

**Do not use `pdf_compare.__version__` to identify the build.** It is maintained by hand in `pdf_compare/__init__.py`, separately from `pyproject.toml`, and has shipped stale in a published release. Trust the distribution metadata instead.

## 3. Before comparing

1. **Establish which file is the original and which is the modified one.** Order matters: the first is drawn on the left with its differences in red, the second on the right in green. If the names or context do not make it obvious, ask.
2. **Choose the output path.** Default to `diff.pdf` in the current directory. Do not overwrite an existing file without saying so; propose another name instead.
3. Check both input paths exist.

## 4. Reading the result

| Output | Meaning | What to do |
|---|---|---|
| `Done. Report size: N MB` | Differences found, report written | Report the path and size |
| `No differences found. No report generated.` | The documents are identical | **No file is created.** Say so plainly; do not go looking for the report |
| `Warning: at least one document has no text layer` | One of them is a scan | The result is **not trustworthy**: differences are detected from extractable text and there is no OCR. Surface this prominently |
| `Error: ...` with exit code 1 | Missing file, not a PDF, encrypted, or no pages | The message is already actionable; pass it on |

A warning about the deprecated `fitz` API is PyMuPDF noise, not a problem with the comparison. Ignore it.

## 5. Limitations worth surfacing when they apply

- **No OCR**: scanned documents, or any PDF without a text layer, cannot be compared.
- **Text only**: changes to images, vector graphics, colours or fonts go undetected when the text is unchanged.
- **Large page shifts**: alignment looks at most `LOOKAHEAD_WINDOW` (3) pages ahead. A block of more than three consecutive inserted or deleted pages mid-document may not be recovered, and everything after it can be reported as changed. If the report shows a wall of differences starting at one specific point, suspect this before believing the document really changed that much.

## 6. Privacy

The documents being compared are usually real ones — contracts, policies, invoices — carrying personal data. **Do not dump their contents** into the conversation or into temporary files: restrict yourself to paths, page numbers, metrics and the report's own labels. All processing is local; nothing is sent over the network.

## 7. Graphical interface

There is also a desktop GUI, resolved the same way:

```bash
uv run --project "$REPO" pdf-compare-gui              # with a working copy
uvx --from "py-pdf-compare@latest" pdf-compare-gui    # without one
```

It needs the system Tk libraries, which are not part of the Python package. On `ImportError: libtk8.6.so`, install them with `sudo pacman -S tk` (Arch), `sudo apt install python3-tk` (Debian/Ubuntu) or `brew install python-tk` (macOS); they are bundled in the official Windows and macOS installers. Propose the command — do not run it yourself, it needs sudo.

## Final check

Report: **which build ran** (working copy with branch and SHA, or the published version), the input paths, the report path — or that no report was produced because the documents are identical — and any missing-text-layer warning.
