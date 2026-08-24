"""Compare whole folders of PDFs, pairing documents by file name."""
import difflib
import html
import os
from datetime import datetime

from pdf_compare.comparator import PDFComparator

# Two stems below this similarity are not the same document under another name.
NAME_SIMILARITY_THRESHOLD = 0.6


def list_pdfs(directory):
    """The PDF files directly inside a directory, sorted by name."""
    return sorted(
        entry for entry in os.listdir(directory)
        if entry.lower().endswith(".pdf")
        and os.path.isfile(os.path.join(directory, entry))
    )


def pair_documents(names_a, names_b, threshold=NAME_SIMILARITY_THRESHOLD):
    """Match documents across two folders by file name.

    Exact stem matches are taken first, so a perfect name can never be stolen
    by a fuzzy one. The rest are matched greedily, best score first, one to one.

    Returns (pairs, unmatched_a, unmatched_b). Anything unmatched is reported,
    never dropped silently: a document with no counterpart is a finding.
    """
    def stem(name):
        """The name without its extension, lowercased: pairing ignores case."""
        return os.path.splitext(name)[0].lower()

    remaining_a, remaining_b = list(names_a), list(names_b)
    pairs = []

    by_stem_b = {}
    for name in remaining_b:
        by_stem_b.setdefault(stem(name), []).append(name)

    for name in list(remaining_a):
        candidates = by_stem_b.get(stem(name))
        if candidates:
            match = candidates.pop(0)
            pairs.append((name, match, 1.0))
            remaining_a.remove(name)
            remaining_b.remove(match)

    # Quadratic in what did NOT match exactly, which looks alarming and is not:
    # measured at 1.9 s for the worst case of 500 x 500 names with no exact
    # match at all, against roughly 0.8 s to compare a single pair of documents.
    # The pairing is never the bottleneck; do not trade its clarity for speed.
    scored = sorted(
        (
            (difflib.SequenceMatcher(None, stem(a), stem(b)).ratio(), a, b)
            for a in remaining_a for b in remaining_b
        ),
        key=lambda item: (-item[0], item[1], item[2]),
    )

    for score, name_a, name_b in scored:
        if score < threshold:
            break
        if name_a in remaining_a and name_b in remaining_b:
            pairs.append((name_a, name_b, score))
            remaining_a.remove(name_a)
            remaining_b.remove(name_b)

    pairs.sort(key=lambda pair: pair[0])
    return pairs, remaining_a, remaining_b


def _unique_diff_name(source_name, used_names):
    """A diff file name that cannot collide with one already written.

    Names are compared case-insensitively because macOS and Windows treat
    "report-diff.pdf" and "REPORT-diff.pdf" as the same file, and the second
    write would silently replace the first.
    """
    stem = os.path.splitext(source_name)[0]
    candidate = f"{stem}-diff.pdf"

    suffix = 2
    while candidate.lower() in used_names:
        candidate = f"{stem}-diff-{suffix}.pdf"
        suffix += 1

    used_names.add(candidate.lower())
    return candidate


def _failed_pair(path_a, path_b, error):
    """The result of a pair that could not be compared at all."""
    return {
        "files": {
            "original": {"name": os.path.basename(path_a), "path": os.path.abspath(path_a), "pages": None},
            "modified": {"name": os.path.basename(path_b), "path": os.path.abspath(path_b), "pages": None},
        },
        "identical": False,
        "missing_text_layer": False,
        "error": f"{type(error).__name__}: {error}",
        "changes": {"pages_added": 0, "pages_removed": 0, "pages_modified": 0,
                    "words_added": 0, "words_removed": 0},
    }


def compare_directories(dir_a, dir_b, output_dir=None, on_progress=None):
    """Compare every matched pair of documents across two folders.

    When output_dir is given, the diff PDF of each differing pair is written
    there. The summary of every pair is returned either way, so the report can
    be produced whether or not the documents were asked for.
    """
    pairs, unmatched_a, unmatched_b = pair_documents(list_pdfs(dir_a), list_pdfs(dir_b))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    results = []
    used_names = set()

    for name_a, name_b, score in pairs:
        path_a = os.path.join(dir_a, name_a)
        path_b = os.path.join(dir_b, name_b)

        comparator = PDFComparator(path_a, path_b)
        try:
            summary, pdf_bytes = comparator.compare(build_pdf=bool(output_dir))
        except Exception as error:
            # One unreadable document must not cost the whole batch. Record it
            # where a human will see it and carry on with the rest.
            summary = _failed_pair(path_a, path_b, error)
            pdf_bytes = None

        diff_name = None
        if pdf_bytes is not None:
            diff_name = _unique_diff_name(name_b, used_names)
            with open(os.path.join(output_dir, diff_name), "wb") as handle:
                handle.write(pdf_bytes)

        summary["match"] = {"name_similarity": round(score, 3)}
        summary["diff_file"] = diff_name
        results.append(summary)

        if on_progress:
            on_progress(summary)

    return {
        "directories": {"original": os.path.abspath(dir_a), "modified": os.path.abspath(dir_b)},
        "output_dir": os.path.abspath(output_dir) if output_dir else None,
        "results": results,
        "unmatched": {"original": unmatched_a, "modified": unmatched_b},
    }


def _totals(batch):
    results = batch["results"]
    failed = [r for r in results if r.get("error")]
    changed = [r for r in results if not r["identical"] and not r.get("error")]
    return {
        "pairs": len(results),
        "changed": len(changed),
        "identical": len(results) - len(changed) - len(failed),
        "failed": len(failed),
        "unreliable": sum(1 for r in results if r["missing_text_layer"]),
        "unmatched": len(batch["unmatched"]["original"]) + len(batch["unmatched"]["modified"]),
    }


def render_html(batch, output_path, generated_at=None):
    """Write a standalone HTML report of a batch comparison."""
    totals = _totals(batch)
    stamp = (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M")
    esc = html.escape

    rows = []
    for result in batch["results"]:
        changes = result["changes"]
        files = result["files"]
        if result.get("error"):
            state = "failed"
        elif result["missing_text_layer"]:
            state = "unreliable"
        else:
            state = "identical" if result["identical"] else "changed"
        label = {"failed": "Could not compare", "unreliable": "No text layer",
                 "identical": "Identical", "changed": "Changed"}[state]

        pages = "&mdash;" if result.get("error") else (
            f"{files['original']['pages']} &rarr; {files['modified']['pages']}")
        detail = (f'<div class="muted err">{esc(result["error"])}</div>'
                  if result.get("error") else "")

        diff_cell = (
            f'<a href="{esc(result["diff_file"])}">{esc(result["diff_file"])}</a>'
            if result["diff_file"] else "&mdash;"
        )
        fuzzy = "" if result["match"]["name_similarity"] == 1.0 else (
            f' <span class="fuzzy" title="matched by name similarity">'
            f'~{result["match"]["name_similarity"]:.2f}</span>'
        )

        rows.append(f"""      <tr class="{state}">
        <td><div>{esc(files['original']['name'])}</div>
            <div class="muted">{esc(files['modified']['name'])}{fuzzy}</div>{detail}</td>
        <td><span class="pill {state}">{label}</span></td>
        <td class="num">{pages}</td>
        <td class="num">+{changes['pages_added']} &minus;{changes['pages_removed']} ~{changes['pages_modified']}</td>
        <td class="num">+{changes['words_added']} &minus;{changes['words_removed']}</td>
        <td>{diff_cell}</td>
      </tr>""")

    unmatched_html = ""
    if totals["unmatched"]:
        items = "".join(
            f"<li><span class='muted'>{esc(side)}</span> {esc(name)}</li>"
            for side, names in (("original", batch["unmatched"]["original"]),
                                ("modified", batch["unmatched"]["modified"]))
            for name in names
        )
        unmatched_html = f"""  <section class="warn">
    <h2>Documents with no counterpart ({totals['unmatched']})</h2>
    <p>These were not compared. A missing counterpart usually means a document was
       added or removed altogether, or that its name changed too much to match.</p>
    <ul>{items}</ul>
  </section>"""

    failed_html = ""
    if totals["failed"]:
        failed_html = f"""  <section class="warn">
    <h2>Could not be compared ({totals['failed']})</h2>
    <p>These pairs raised an error and were skipped; the rest of the batch was
       unaffected. A protected or corrupt document is the usual cause. The reason
       is shown next to each one in the table below.</p>
  </section>"""

    unreliable_html = ""
    if totals["unreliable"]:
        unreliable_html = f"""  <section class="warn">
    <h2>Unreliable comparisons ({totals['unreliable']})</h2>
    <p>One of the documents has no extractable text, so differences cannot be
       detected. Such a pair looks identical whether or not it is.</p>
  </section>"""

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PDF comparison report</title>
<style>
  :root {{ color-scheme: light dark; --line:#d8dce3; --muted:#6b7280; --bg:#fff; --fg:#111;
           --changed:#b45309; --identical:#047857; --unreliable:#b91c1c; --accent:#f6f7f9; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --line:#333a44; --muted:#9aa3af; --bg:#14161a; --fg:#e8eaed; --accent:#1c1f25;
             --changed:#fbbf24; --identical:#34d399; --unreliable:#f87171; }} }}
  body {{ margin:0 auto; padding:2rem 1.25rem; max-width:70rem; background:var(--bg); color:var(--fg);
          font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  h1 {{ font-size:1.5rem; margin:0 0 .25rem; }}
  .muted {{ color:var(--muted); font-size:.87em; }}
  .cards {{ display:flex; flex-wrap:wrap; gap:.75rem; margin:1.5rem 0; }}
  .card {{ flex:1 1 8rem; border:1px solid var(--line); border-radius:.5rem; padding:.75rem 1rem; }}
  .card b {{ display:block; font-size:1.6rem; font-weight:600; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ border-collapse:collapse; width:100%; }}
  th,td {{ text-align:left; padding:.55rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
  td.num {{ font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .pill {{ display:inline-block; padding:.1rem .5rem; border-radius:999px; font-size:.8rem;
           border:1px solid currentColor; }}
  .pill.changed {{ color:var(--changed); }}
  .pill.identical {{ color:var(--identical); }}
  .pill.unreliable {{ color:var(--unreliable); }}
  .pill.failed {{ color:var(--unreliable); }}
  .err {{ color:var(--unreliable); }}
  .fuzzy {{ color:var(--changed); }}
  .warn {{ border:1px solid var(--line); border-left:3px solid var(--changed);
           background:var(--accent); border-radius:.4rem; padding:.75rem 1rem; margin:1.5rem 0; }}
  .warn h2 {{ font-size:1rem; margin:0 0 .35rem; }}
  .warn ul {{ margin:.5rem 0 0; padding-left:1.1rem; }}
  footer {{ margin-top:2.5rem; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
  <h1>PDF comparison report</h1>
  <p class="muted">{esc(batch['directories']['original'])} &rarr; {esc(batch['directories']['modified'])}<br>{stamp}</p>

  <div class="cards">
    <div class="card"><b>{totals['pairs']}</b><span class="muted">pairs compared</span></div>
    <div class="card"><b>{totals['changed']}</b><span class="muted">with differences</span></div>
    <div class="card"><b>{totals['identical']}</b><span class="muted">identical</span></div>
    <div class="card"><b>{totals['unmatched']}</b><span class="muted">unmatched</span></div>
    <div class="card"><b>{totals['failed']}</b><span class="muted">could not compare</span></div>
  </div>

{failed_html}
{unreliable_html}
{unmatched_html}
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Documents</th><th>Result</th><th>Pages</th><th>Page changes</th><th>Word changes</th><th>Diff</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows) if rows else '      <tr><td colspan="6" class="muted">No comparable documents found.</td></tr>'}
    </tbody>
  </table>
  </div>

  <footer>Differences are detected from extractable text; scanned documents cannot be compared.
  Counts are reported rather than a similarity percentage, so you can derive whatever ratio you need.</footer>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(document)

    return totals
