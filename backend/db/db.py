"""SB-47: create/check a local SQLite metadata database; never import media."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
import unicodedata

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
MIN_SQLITE = (3, 37, 0)


def connect(database: str | Path) -> sqlite3.Connection:
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        raise RuntimeError("SQLite >=3.37 is required (STRICT tables); update Python/SQLite.")
    conn = sqlite3.connect(str(database), timeout=10)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA recursive_triggers=ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        conn.close()
        raise RuntimeError("Foreign-key enforcement could not be enabled.")
    return conn


def normalize_turkish(value: str, *, uppercase: bool = False) -> str:
    """For future ingestion: preserve Turkish letters; no accent/diacritic removal."""
    value = unicodedata.normalize("NFC", value.strip())
    if not value:
        raise ValueError("Text must not be empty.")
    if uppercase:
        value = value.translate(str.maketrans({"i": "İ", "ı": "I"})).upper()
    return value


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS) -> list[str]:
    if conn.in_transaction:
        raise RuntimeError("Run migrations outside an application transaction.")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables - {"sqlite_sequence"} and "schema_migration" not in tables:
        raise RuntimeError("Refusing an existing unversioned database; use a new empty database path.")
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migration (
        name TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    ) STRICT""")
    conn.commit()
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not files:
        raise RuntimeError("No migration files found.")
    recorded = dict(conn.execute("SELECT name,sha256 FROM schema_migration"))
    if set(recorded) - {p.name for p in files}:
        raise RuntimeError("Applied migration missing from this checkout.")
    applied = []
    for path in files:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if path.name in recorded:
            if recorded[path.name] != digest:
                raise RuntimeError(f"Applied migration changed: {path.name}; add a new migration instead.")
            continue
        # Only checked-in filenames/digests enter this SQL; values are quoted anyway.
        name_sql = path.name.replace("'", "''")
        script = ("BEGIN IMMEDIATE;\n" + raw.decode("utf-8") +
                  f"\nINSERT INTO schema_migration(name,sha256) VALUES ('{name_sql}','{digest}');\nCOMMIT;")
        try:
            conn.executescript(script)
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        applied.append(path.name)
    return applied


def check(conn: sqlite3.Connection) -> dict:
    expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))}
    actual = dict(conn.execute("SELECT name,sha256 FROM schema_migration"))
    if not expected or actual != expected:
        raise RuntimeError("Migration ledger differs from this checkout; run init or use the matching revision.")
    integrity = [r[0] for r in conn.execute("PRAGMA integrity_check")]
    foreign_keys = list(conn.execute("PRAGMA foreign_key_check"))
    if integrity != ["ok"] or foreign_keys:
        raise RuntimeError(f"Database check failed: integrity={integrity}, foreign_keys={foreign_keys}")
    tables = sorted(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    return {"sqlite_version": sqlite3.sqlite_version,
            "foreign_keys": conn.execute("PRAGMA foreign_keys").fetchone()[0],
            "recursive_triggers": conn.execute("PRAGMA recursive_triggers").fetchone()[0],
            "integrity_check": integrity, "foreign_key_violations": len(foreign_keys),
            "tables": tables}


def export_lexicon(conn: sqlite3.Connection, *, development: bool = False) -> dict:
    """Preserve the SoW JSON interface; reviewed metadata is not proof of asset quality."""
    output = {}
    for sign_id, gloss, definition, domain, variant, status in conn.execute(
        "SELECT sign_id,gloss,definition_tr,domain,variant_code,review_status "
        "FROM sign_entry WHERE is_active=1 ORDER BY sign_id"
    ):
        equivalents = [r[0] for r in conn.execute(
            "SELECT equivalent_tr FROM sign_equivalent WHERE sign_id=? ORDER BY equivalent_tr", (sign_id,))]
        clips = list(conn.execute(
            "SELECT asset_path,review_status FROM animation_clip WHERE sign_id=? AND is_default=1", (sign_id,)))
        if len(clips) > 1:
            raise RuntimeError(f"Multiple default clips for {sign_id}.")
        eligible = status == "expert_reviewed" and clips and clips[0][1] == "expert_reviewed"
        if not development and not (eligible and equivalents):
            continue
        texts = [gloss, definition] + equivalents
        if any(unicodedata.normalize("NFC", value) != value for value in texts):
            raise RuntimeError(f"Non-NFC lexical text for {sign_id}; normalize during ingestion.")
        if normalize_turkish(gloss, uppercase=True) != gloss:
            raise RuntimeError(f"Gloss is not a Turkish-uppercase label for {sign_id}.")
        output[sign_id] = {"sign_id": sign_id, "gloss": gloss,
            "turkish_equivalents": equivalents, "definition_tr": definition,
            "domain": domain, "variant_code": variant,
            "clip_file": clips[0][0] if eligible else None,
            "review_status": status}
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "check", "export"))
    parser.add_argument("--db", required=True, type=Path, help="Private local database file (outside git).")
    parser.add_argument("--out", type=Path, help="New JSON dictionary output path, required for export.")
    parser.add_argument("--development", action="store_true", help="Explicitly include draft dictionary records.")
    args = parser.parse_args(argv)
    database = args.db.expanduser().resolve()
    try:
        if args.command != "init" and not database.is_file():
            raise RuntimeError("Database not found; check/export do not create a database.")
        if args.command == "export" and args.out is None:
            raise RuntimeError("export requires --out; existing output files are never overwritten.")
        if args.command != "export" and (args.out is not None or args.development):
            raise RuntimeError("--out and --development apply only to export.")
        if args.command == "init":
            database.parent.mkdir(parents=True, exist_ok=True)
        with closing(connect(database)) as conn:
            applied = migrate(conn) if args.command == "init" else []
            result = check(conn)
            if "schema_migration" not in result["tables"]:
                raise RuntimeError("Database has no SB-47 migration ledger.")
            if args.command == "export":
                payload = export_lexicon(conn, development=args.development)
                target = args.out.expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                result.update(export=str(target), records=len(payload), development=args.development)
            result.update(database=str(database), applied=applied)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, sqlite3.Error, UnicodeError) as exc:
        print(f"SB-47 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
