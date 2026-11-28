"""SB-51: import dataset class mapping, labels and splits into the SB-47 schema.

Reads the SB-46 file formats:
  * class mapping CSV with header ``ClassId,TR,EN``
  * one headerless ``sample_id,class_id`` label CSV per split
    (sample IDs ``signerX_sampleY``)
and writes ``dataset_release``, ``dataset_class``, ``dataset_split``,
``dataset_signer_split`` and ``video_sample`` rows in one transaction. It never
writes ``dataset_mapping`` or ``sign_entry`` (README "SB-51 import boundary",
item 3), never copies or decodes media and uses only the standard library.

Re-running with the same inputs adds no rows. A row that already exists with
different content is reported and the whole import is rolled back. After the
import, counts read from the input files are compared with database row counts
(and with ``--expect`` if given), and ``db.check`` is run.

Exit codes: 0 = imported and all counts match; 1 = input/database error, nothing
written; 2 = refused output path; 3 = imported, but a count difference or a
missing media file was reported.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

SPLITS = ("train", "validation", "test")
SPLIT_FOLDERS = {"train": "train", "validation": "val", "test": "test"}  # SB-46 / README item 5
MAPPING_HEADER = ["ClassId", "TR", "EN"]
SAMPLE_ID = re.compile(r"^(signer\d+)_sample\d+$")
FORBIDDEN_VERSIONS = {"latest", "unknown", "tbd"}
DEFAULT_USAGE = (
    "Academic, non-commercial use only; cite the dataset and the relevant challenge "
    "distribution; comply with the provider's terms; no redistribution of the dataset "
    "or derived data (including landmarks) without explicit permission "
    "(SB-16 access request, SB-46 handling conditions)."
)
DEFAULT_SOURCE = "Provider class mapping and split label files as verified in SB-46"
EXPECT_KEYS = (set(SPLITS) | {f"{s}_signers" for s in SPLITS} | {f"{s}_classes" for s in SPLITS}
               | {"samples", "classes", "signers"})


class InputError(Exception):
    """Input or consistency error: nothing is written."""

    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


# ---------------------------------------------------------------- input files

def read_mapping(path: Path) -> dict[str, tuple[str | None, str | None]]:
    """ClassId -> (TR, EN). Names are kept exactly as in the source file."""
    classes: dict[str, tuple[str | None, str | None]] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = csv.reader(fh)
        header = next(rows, None)
        if header is None or [h.strip() for h in header] != MAPPING_HEADER:
            raise InputError(f"{path}: first row must be the header {','.join(MAPPING_HEADER)}, got {header}")
        for lineno, row in enumerate(rows, start=2):
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) != 3:
                raise InputError(f"{path}:{lineno}: expected 3 columns (ClassId,TR,EN), got {len(row)}")
            class_id = row[0].strip()
            if not class_id:
                raise InputError(f"{path}:{lineno}: empty ClassId")
            if class_id in classes:
                raise InputError(f"{path}:{lineno}: duplicate ClassId {class_id!r}")
            classes[class_id] = (row[1] or None, row[2] or None)
    if not classes:
        raise InputError(f"{path}: no classes found")
    return classes


def read_labels(path: Path, classes: dict) -> list[tuple[str, str, str]]:
    """Headerless sample_id,class_id -> [(sample_id, class_id, signer_id)]."""
    samples = []
    seen: set[str] = set()
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for lineno, row in enumerate(csv.reader(fh), start=1):
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) != 2:
                raise InputError(f"{path}:{lineno}: expected 2 columns (sample_id,class_id), got {len(row)}")
            sample_id, class_id = row[0].strip(), row[1].strip()
            match = SAMPLE_ID.match(sample_id)
            if not match:
                if lineno == 1:
                    raise InputError(f"{path}:1: header row or invalid sample_id {sample_id!r}; "
                                       "label files must be headerless with signerX_sampleY IDs")
                raise InputError(f"{path}:{lineno}: invalid sample_id {sample_id!r} (expected signerX_sampleY)")
            if sample_id in seen:
                raise InputError(f"{path}:{lineno}: duplicate sample_id {sample_id!r}")
            if class_id not in classes:
                raise InputError(f"{path}:{lineno}: class_id {class_id!r} is not in the class mapping")
            seen.add(sample_id)
            samples.append((sample_id, class_id, match.group(1)))
    return samples


def load_inputs(mapping_path: Path, label_paths: dict[str, Path]):
    classes = read_mapping(mapping_path)
    splits = {split: read_labels(path, classes) for split, path in label_paths.items()}
    sample_split: dict[str, str] = {}
    signer_split: dict[str, str] = {}
    for split, samples in splits.items():
        for sample_id, _, signer in samples:
            if sample_id in sample_split:
                raise InputError(f"sample_id {sample_id!r} appears in both {sample_split[sample_id]} and {split}")
            sample_split[sample_id] = split
            if signer_split.setdefault(signer, split) != split:
                raise InputError(f"signer {signer!r} appears in both {signer_split[signer]} and {split}; "
                                   "splits must be signer-independent")
    return classes, splits


def sample_paths(split: str, sample_id: str) -> tuple[str, str]:
    folder = SPLIT_FOLDERS[split]
    return f"{folder}/{sample_id}_color.mp4", f"{folder}/{sample_id}_depth.mp4"


def media_size(root: Path, rel: str) -> tuple[int | None, str | None]:
    """Return (bytes, problem). The file must be a regular file inside root."""
    path = root / rel
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None, "missing"
    if not resolved.is_relative_to(root.resolve()):
        return None, "resolves outside media root"
    if not resolved.is_file():
        return None, "not a regular file"
    size = resolved.stat().st_size
    return (size, None) if size > 0 else (None, "zero bytes")


# ---------------------------------------------------------------- database

def _ensure(conn, table: str, key: dict, values: dict, stats: dict, diffs: list[str],
            compare_skip: set[str] = frozenset()) -> None:
    """Insert the row if absent; if present, record differences instead of overwriting."""
    where = " AND ".join(f"{k}=?" for k in key)
    cols = list(values)
    existing = conn.execute(f"SELECT {', '.join(cols) or '1'} FROM {table} WHERE {where}",
                            tuple(key.values())).fetchone()
    if existing is None:
        all_cols = list(key) + cols
        conn.execute(f"INSERT INTO {table}({', '.join(all_cols)}) VALUES ({', '.join('?' * len(all_cols))})",
                     tuple(key.values()) + tuple(values.values()))
        stats.setdefault(table, {"inserted": 0, "unchanged": 0})["inserted"] += 1
        return
    changed = [f"{c}: database={old!r}, input={new!r}"
               for c, old, new in zip(cols, existing, values.values())
               if c not in compare_skip and old != new]
    if changed:
        label = ", ".join(f"{k}={v}" for k, v in key.items() if k not in ("dataset_name", "dataset_version"))
        diffs.append(f"{table} [{label or 'release'}] " + "; ".join(changed))
    else:
        stats.setdefault(table, {"inserted": 0, "unchanged": 0})["unchanged"] += 1


def import_rows(conn, release: dict, classes, splits, media_root: Path | None):
    """Write all rows inside the caller's transaction. Raises InputError on conflicts."""
    name, version = release["dataset_name"], release["dataset_version"]
    rk = {"dataset_name": name, "dataset_version": version}
    stats: dict = {}
    diffs: list[str] = []
    media_issues: list[dict] = []

    _ensure(conn, "dataset_release", rk,
            {k: release[k] for k in ("description", "source_reference", "usage_conditions")}, stats, diffs)
    for class_id, (tr, en) in classes.items():
        _ensure(conn, "dataset_class", {**rk, "original_label": class_id},
                {"name_tr": tr, "name_en": en}, stats, diffs)
    for split, samples in splits.items():
        _ensure(conn, "dataset_split", {**rk, "split_name": split}, {}, stats, diffs)
        for signer in sorted({s[2] for s in samples}):
            _ensure(conn, "dataset_signer_split", {**rk, "signer_id": signer},
                    {"split_name": split}, stats, diffs)
    if diffs:  # report release/class/signer conflicts before sample inserts hit foreign keys
        raise InputError(f"{len(diffs)} existing row(s) differ from the input; nothing was overwritten",
                         diffs)
    for split, samples in splits.items():
        for sample_id, class_id, signer in samples:
            color, depth = sample_paths(split, sample_id)
            color_bytes = depth_bytes = None
            if media_root is not None:
                color_bytes, problem_c = media_size(media_root, color)
                depth_bytes, problem_d = media_size(media_root, depth)
                for rel, problem in ((color, problem_c), (depth, problem_d)):
                    if problem:
                        media_issues.append({"sample_id": sample_id, "path": rel, "problem": problem})
            _ensure(conn, "video_sample", {**rk, "sample_id": sample_id},
                    {"original_label": class_id, "signer_id": signer, "split_name": split,
                     "color_path": color, "depth_path": depth,
                     "color_bytes": color_bytes, "depth_bytes": depth_bytes},
                    stats, diffs,
                    compare_skip=set() if media_root is not None else {"color_bytes", "depth_bytes"})
    if diffs:
        raise InputError(f"{len(diffs)} existing row(s) differ from the input; nothing was overwritten",
                           diffs)
    return stats, media_issues


def file_counts(classes, splits) -> dict:
    per_split = {s: {"samples": len(rows), "signers": len({r[2] for r in rows}),
                     "classes": len({r[1] for r in rows})} for s, rows in splits.items()}
    every = [r for rows in splits.values() for r in rows]
    return {"per_split": per_split,
            "total": {"samples": len(every), "signers": len({r[2] for r in every}),
                      "classes": len(classes)}}


def db_counts(conn, name: str, version: str, split_names) -> dict:
    rk = (name, version)
    per_split = {}
    for s in split_names:
        per_split[s] = {
            "samples": conn.execute("SELECT count(*) FROM video_sample WHERE dataset_name=? AND "
                                    "dataset_version=? AND split_name=?", rk + (s,)).fetchone()[0],
            "signers": conn.execute("SELECT count(*) FROM dataset_signer_split WHERE dataset_name=? AND "
                                    "dataset_version=? AND split_name=?", rk + (s,)).fetchone()[0],
            "classes": conn.execute("SELECT count(DISTINCT original_label) FROM video_sample WHERE "
                                    "dataset_name=? AND dataset_version=? AND split_name=?",
                                    rk + (s,)).fetchone()[0],
        }
    total = {
        "samples": conn.execute("SELECT count(*) FROM video_sample WHERE dataset_name=? AND dataset_version=?",
                                rk).fetchone()[0],
        "signers": conn.execute("SELECT count(*) FROM dataset_signer_split WHERE dataset_name=? AND "
                                "dataset_version=?", rk).fetchone()[0],
        "classes": conn.execute("SELECT count(*) FROM dataset_class WHERE dataset_name=? AND dataset_version=?",
                                rk).fetchone()[0],
    }
    return {"per_split": per_split, "total": total}


def compare_counts(files: dict, database: dict, expect: dict[str, int] | None) -> list[dict]:
    """One row per compared metric: files vs database, plus expected when given."""
    expect = expect or {}
    rows, used = [], set()

    def add(metric, split, f, d, expected_key):
        used.add(expected_key)
        exp = expect.get(expected_key)
        ok = f == d and (exp is None or exp == d)
        rows.append({"metric": metric, "split": split, "files": f, "database": d,
                     "expected": exp, "status": "match" if ok else "DIFFERENCE"})

    for split, counts in files["per_split"].items():
        for metric in ("samples", "signers", "classes"):
            key = split if metric == "samples" else f"{split}_{metric}"
            add(metric, split, counts[metric], database["per_split"][split][metric], key)
    for metric in ("samples", "signers", "classes"):
        add(metric, "total", files["total"][metric], database["total"][metric], metric)
    for key in sorted(set(expect) - used):  # expectation for a split not given in --labels
        rows.append({"metric": key, "split": "-", "files": None, "database": None,
                     "expected": expect[key], "status": "DIFFERENCE (split not imported in this run)"})
    return rows


# ---------------------------------------------------------------- repository guard

def find_repo_root(path: Path) -> Path | None:
    p = Path(path).expanduser().resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def is_gitignored(path: Path, root: Path) -> bool:
    rel = Path(path).expanduser().resolve().relative_to(root).as_posix()
    try:
        res = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", rel],
                             capture_output=True, check=False)
    except FileNotFoundError:
        return False
    return res.returncode == 0


def unsafe_paths(paths, ignored=is_gitignored) -> list[str]:
    unsafe = []
    for p in paths:
        if p is None:
            continue
        root = find_repo_root(p)
        if root is not None and not ignored(p, root):
            unsafe.append(str(p))
    return unsafe


# ---------------------------------------------------------------- CLI

def parse_labels(values: list[str]) -> dict[str, Path]:
    out = {}
    for item in values:
        split, sep, path = item.partition("=")
        if not sep or split not in SPLITS or not path:
            raise InputError(f"--labels entries must be split=path with split in {SPLITS}; got {item!r}")
        if split in out:
            raise InputError(f"--labels: split {split!r} given twice")
        out[split] = Path(path).expanduser()
    if not out:
        raise InputError("--labels needs at least one split=path")
    return dict(sorted(out.items(), key=lambda kv: SPLITS.index(kv[0])))


def parse_expect(text: str | None) -> dict[str, int] | None:
    if not text:
        return None
    out = {}
    for part in text.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep or key not in EXPECT_KEYS:
            raise InputError(f"--expect: unknown entry {part!r}; allowed keys: {', '.join(sorted(EXPECT_KEYS))}")
        try:
            out[key] = int(value)
        except ValueError:
            raise InputError(f"--expect: {key} must be an integer, got {value!r}") from None
    return out


def check_version(version: str) -> str:
    v = version.strip()
    if not v or v.lower() in FORBIDDEN_VERSIONS:
        raise InputError(f"--dataset-version {version!r} is not allowed; use a pinned provider version "
                           "or an explicit local snapshot ID (with --local-snapshot)")
    return v


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SB-51 dataset label/metadata import (standard library only)")
    p.add_argument("--db", required=True, type=Path, help="private SQLite file (outside git)")
    p.add_argument("--dataset-name", default="AUTSL")
    p.add_argument("--dataset-version", required=True,
                   help="pinned provider version or a team-defined local snapshot ID")
    p.add_argument("--local-snapshot", action="store_true",
                   help="declare --dataset-version as a local snapshot ID, not a provider version")
    p.add_argument("--description", help="dataset_release.description")
    p.add_argument("--source-reference", default=DEFAULT_SOURCE)
    p.add_argument("--usage-conditions", default=DEFAULT_USAGE)
    p.add_argument("--mapping", required=True, type=Path, help="class mapping CSV (ClassId,TR,EN)")
    p.add_argument("--labels", required=True, nargs="+", metavar="SPLIT=PATH",
                   help="train=..., validation=..., test=... (at least one)")
    p.add_argument("--media-root", type=Path, help="private media root; checks files and records byte sizes")
    p.add_argument("--expect", help="e.g. train=28142,validation=4418,test=3742,classes=226,signers=43")
    p.add_argument("--report", type=Path, help="JSON report path (outside git)")
    return p


def release_record(args, version: str) -> dict:
    description = args.description or f"{args.dataset_name} class labels and split metadata (SB-51 import)"
    if args.local_snapshot:
        description += (f" Dataset version '{version}' is a team-defined local snapshot ID, "
                        "not a provider-issued version.")
    return {"dataset_name": args.dataset_name.strip(), "dataset_version": version,
            "description": description, "source_reference": args.source_reference,
            "usage_conditions": args.usage_conditions}


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report: dict = {"tool": "backend/db/import_dataset.py", "issue": "SB-51",
                    "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    unsafe = unsafe_paths([args.db, args.report])
    if unsafe:
        print("SB-51 refused: these paths are inside the git repository and not gitignored:", file=sys.stderr)
        for p in unsafe:
            print(f"  {p}", file=sys.stderr)
        print("Keep databases and reports outside the checkout (SB-16, SB-46, SB-47).", file=sys.stderr)
        return 2

    exit_code = 1
    try:
        version = check_version(args.dataset_version)
        release = release_record(args, version)
        label_paths = parse_labels(args.labels)
        expect = parse_expect(args.expect)
        classes, splits = load_inputs(args.mapping, label_paths)
        report.update(dataset_name=release["dataset_name"], dataset_version=version,
                      local_snapshot=args.local_snapshot,
                      inputs={"mapping": {"name": args.mapping.name, "sha256": sha256(args.mapping)},
                              "labels": {s: {"name": p.name, "sha256": sha256(p)}
                                         for s, p in label_paths.items()},
                              "media_root_checked": args.media_root is not None})

        database = args.db.expanduser().resolve()
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(db.connect(database)) as conn:
            report["migrations_applied"] = db.migrate(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                stats, media_issues = import_rows(conn, release, classes, splits,
                                                  args.media_root.expanduser() if args.media_root else None)
                files = file_counts(classes, splits)
                database_counts = db_counts(conn, release["dataset_name"], version, splits)
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            report["check"] = db.check(conn)

        comparison = compare_counts(files, database_counts, expect)
        differences = [r for r in comparison if r["status"] != "match"]
        report.update(rows=stats, file_counts=files, database_counts=database_counts,
                      expected=expect, comparison=comparison, differences=differences,
                      media_issues=media_issues)
        exit_code = 3 if differences or media_issues else 0
        report["status"] = "ok" if exit_code == 0 else "imported_with_differences"
    except InputError as exc:
        report.update(status="failed", error=str(exc), error_details=exc.details,
                      note="transaction rolled back; nothing was written")
    except (OSError, RuntimeError, sqlite3.Error, UnicodeError) as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                      note="transaction rolled back; nothing was written")
    report["exit_code"] = exit_code

    print_report(report)
    if args.report:
        target = args.report.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {target}")
    return exit_code


def print_report(report: dict) -> None:
    if report.get("status") == "failed":
        print(f"SB-51 import FAILED: {report['error']}", file=sys.stderr)
        for d in report.get("error_details", []):
            print(f"  - {d}", file=sys.stderr)
        print("Transaction rolled back; nothing was written.", file=sys.stderr)
        return
    print(f"SB-51 import: {report['dataset_name']} / {report['dataset_version']}")
    for table, s in report["rows"].items():
        print(f"  {table:<22} inserted {s['inserted']:>6}, unchanged {s['unchanged']:>6}")
    print("Count comparison (files vs database [vs expected]):")
    for r in report["comparison"]:
        exp = "" if r["expected"] is None else f" expected={r['expected']}"
        print(f"  {r['split']:<10} {r['metric']:<9} files={r['files']} database={r['database']}{exp}  {r['status']}")
    if report["media_issues"]:
        print(f"Media issues: {len(report['media_issues'])}")
        for m in report["media_issues"][:20]:
            print(f"  {m['path']}: {m['problem']}")
        if len(report["media_issues"]) > 20:
            print(f"  ... {len(report['media_issues']) - 20} more (see --report)")
    c = report["check"]
    print(f"db.check: integrity={c['integrity_check']}, foreign_key_violations={c['foreign_key_violations']}")
    print(f"Result: {report['status']} (exit {report['exit_code']})")


if __name__ == "__main__":
    raise SystemExit(run())
