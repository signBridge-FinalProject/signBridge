#!/usr/bin/env python3
"""SB-48 scenario coverage audit against the AUTSL class list.

What the script does
--------------------
1. Reads the local AUTSL class list and the three label files. All paths are
   command-line arguments; no machine-specific path is stored in the code.
2. Validates every input before writing anything. On any error it prints the
   problems and exits with status 2 without creating or overwriting outputs:
   - class list: header must be ClassId,TR,EN; ClassId must be an integer;
     no duplicate ClassId; no empty or duplicate (case/diacritic-folded) TR name;
   - label files: every row has exactly two columns (sample_id,class_id); the
     class ID is an integer present in the class list; no duplicate sample ID
     within a split or across splits;
   - curated tables below: a gloss curated as found / needs linguistic check
     must have its class; a gloss curated as not found must not match a class
     name; every candidate class must exist.
3. Counts labelled samples per class and split by sample ID (one label row is
   one sample; colour and depth videos are not counted separately). Classes in
   the class list with zero samples in a split are counted as 0 and included in
   the minimum.
4. Writes four CSV files (only the audited classes, never the full class list
   or the raw labels):
   - coverage-glosses.csv    one row per audited gloss: source, category,
                             AUTSL ClassId/TR/EN, train/validation/test counts,
                             rationale;
   - coverage-summary.csv    per-scenario coverage (numerator/denominator,
                             tokens, not-found and needs-check lists);
   - candidate-classes.csv   candidate replacement classes named in
                             happy-paths.md §2, with sample counts;
   - label-checks.csv        the label-file checks above, per split.

What the script does not do
---------------------------
The categories (found / not found / needs linguistic check) and the meaning
judgements in GLOSSES are human-curated decisions recorded in this file. The
script only checks them for consistency with the class list. It does not verify
that an AUTSL sign is the intended TİD sign, and it does not open any video.
Test-split counts are a descriptive inventory only; they must not be used to
choose the vocabulary or tune a model.

Usage
-----
  python coverage_audit.py --signlist <SignList_ClassId_TR_EN.csv> \
      --train <train_labels.csv> --validation <validation/ground_truth.csv> \
      --test <test/ground_truth.csv> --out <output-dir>
"""
import argparse
import collections
import csv
import os
import sys

FOUND, NOT_FOUND, CHECK = "found", "not found", "needs linguistic check"
# Mapping to Proposal R6 Methods 1 (c) / SB-18 Supporting Technical Notes §1.1
METHOD = {FOUND: "exact (provisional, name level)", CHECK: "uncertain", NOT_FOUND: "missing"}

# Direction A signed input of each happy path (docs/sow/happy-paths.md flow tables).
# Tokens in signing order; a gloss repeated within a scenario is counted once in the denominator.
SCENARIOS = {
    "HP-1": ("Hospital desk (Ayşe)", "happy-paths.md §3 step 2", ["HASTANE", "DOKTOR", "YARDIM"]),
    "HP-2": ("Pharmacy counter (customer)", "happy-paths.md §4 step 4", ["İLAÇ", "YARIN", "Mİ"]),
    "HP-3": ("Classroom, Emre signing (Zeynep)", "happy-paths.md §5 step 2", ["YARIN", "OKUL", "BULUŞMAK", "Mİ"]),
    "HP-4": ("Café order (Can)", "happy-paths.md §6 step 2", ["ÇAY", "BİR", "SİMİT", "BİR", "LÜTFEN"]),
}
# HP-3P (proposed, D-23) repeats the HP-3 signed input (happy-paths.md §5.1 step 3); not counted again.

# Human-curated decisions: gloss -> (category, expected AUTSL TR label or None, rationale)
GLOSSES = {
    "HASTANE": (FOUND, "hastane", "Same class name; EN label 'hospital' agrees with the intended meaning. Name level only."),
    "DOKTOR": (FOUND, "doktor", "Same class name; EN label 'doctor' agrees. Name level only."),
    "YARDIM": (FOUND, "yardim", "Same class name; EN label 'help' agrees. Name level only."),
    "İLAÇ": (FOUND, "ilac", "Same class name; EN label 'medicine' agrees. Name level only."),
    "YARIN": (FOUND, "yarin", "Same class name; EN label 'tomorrow' agrees. Name level only."),
    "OKUL": (FOUND, "okul", "Same class name; EN label 'school' agrees. Name level only."),
    "ÇAY": (FOUND, "cay", "Same class name; EN label 'tea' agrees. Name level only."),
    "Mİ": (NOT_FOUND, None, "No class for the question particle. This does not show that TİD needs a separate manual question sign; whether the question can be formed without one is an open linguistic question."),
    "BULUŞMAK": (NOT_FOUND, None, "No class 'bulusmak' or spelling variant."),
    "BİR": (NOT_FOUND, None, "No number classes. The single 'saat' (hour) class does not cover numbers or clock times."),
    "SİMİT": (NOT_FOUND, None, "No class 'simit'."),
    "LÜTFEN": (NOT_FOUND, None, "No class 'lutfen'. 'rica_etmek' (request) is a candidate replacement, not a verified synonym."),
    # Documented scenario vocabulary outside the happy-path signed input
    "ECZANE": (FOUND, "eczane", "Pharmacy word (Proposal R6 Methods 1 (c); SB-14). EN label 'pharmacy' agrees. Name level only."),
    "TEŞEKKÜR": (FOUND, "tesekkur", "SB-14 example entry. EN label 'thanks' agrees. Name level only."),
    "SAAT": (CHECK, "saat", "Single class 'saat' (EN 'hour'). Whether it is the sign intended for appointment or clock-time use needs checking; it does not cover numbers or clock times."),
    "RANDEVU": (NOT_FOUND, None, "Hospital word; no class (Proposal R6 Methods 1 (c); SB-14)."),
    "KARIN": (NOT_FOUND, None, "Hospital word; no class (Proposal R6 Methods 1 (c))."),
    "AĞRI": (NOT_FOUND, None, "Hospital word; no class (Proposal R6 Methods 1 (c))."),
    "GİTMEK": (NOT_FOUND, None, "No class (Proposal R6 Methods 1 (c); SB-14)."),
    "SU": (NOT_FOUND, None, "SB-14 example entry; no class."),
    "BUGÜN": (NOT_FOUND, None, "SB-14 example entry; no class."),
}
DOCUMENTED = {
    "ECZANE": "Proposal R6 Methods 1 (c); SB-14",
    "TEŞEKKÜR": "SB-14",
    "SAAT": "Proposal R6 Methods 1 (c); Tech Notes §1.1",
    "RANDEVU": "Proposal R6 Methods 1 (c); SB-14",
    "KARIN": "Proposal R6 Methods 1 (c)",
    "AĞRI": "Proposal R6 Methods 1 (c)",
    "GİTMEK": "Proposal R6 Methods 1 (c); SB-14",
    "SU": "SB-14",
    "BUGÜN": "SB-14",
}
# Candidate replacement classes named in happy-paths.md §2 (not verified synonyms)
CANDIDATES = {
    "beraber": "HP-3", "arkadas": "HP-3", "nerede": "HP-3", "saat": "HP-3", "olur": "HP-3", "tamam": "HP-3",
    "rica_etmek": "HP-4", "tesekkur": "HP-4", "para": "HP-4", "seker": "HP-4", "sut": "HP-4", "bardak": "HP-4",
}

TR_FOLD = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ç": "c", "ç": "c", "Ğ": "g", "ğ": "g",
                         "Ö": "o", "ö": "o", "Ş": "s", "ş": "s", "Ü": "u", "ü": "u"})


def fold(s):
    return s.translate(TR_FOLD).lower().strip()


def load_classes(path, errors):
    classes, names = {}, {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != ["ClassId", "TR", "EN"]:
            errors.append(f"class list: header must be ClassId,TR,EN, got {header}")
            return classes, names
        for n, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != 3:
                errors.append(f"class list line {n}: expected 3 columns, got {len(row)}")
                continue
            try:
                cid = int(row[0])
            except ValueError:
                errors.append(f"class list line {n}: ClassId '{row[0]}' is not an integer")
                continue
            tr, en = row[1].strip(), row[2].strip()
            if cid in classes:
                errors.append(f"class list line {n}: duplicate ClassId {cid}")
                continue
            if not tr or not en:
                errors.append(f"class list line {n}: empty TR or EN name for ClassId {cid}")
                continue
            key = fold(tr)
            if key in names:
                errors.append(f"class list line {n}: duplicate TR name '{tr}' (also ClassId {names[key]})")
                continue
            classes[cid] = (tr, en)
            names[key] = cid
    if not classes and not errors:
        errors.append("class list: no classes found")
    return classes, names


def load_labels(split, path, classes, errors):
    ids, counts = [], collections.Counter()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for n, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue
            if len(row) != 2:
                errors.append(f"{split} line {n}: expected 2 columns (sample_id,class_id), got {len(row)}")
                continue
            sid = row[0].strip()
            try:
                cid = int(row[1])
            except ValueError:
                errors.append(f"{split} line {n}: class_id '{row[1]}' is not an integer")
                continue
            if cid not in classes:
                errors.append(f"{split} line {n}: class_id {cid} is not in the class list")
                continue
            ids.append(sid)
            counts[cid] += 1
    dup = [s for s, c in collections.Counter(ids).items() if c > 1]
    if dup:
        errors.append(f"{split}: {len(dup)} duplicate sample IDs, e.g. {dup[:3]}")
    return ids, counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("signlist", "train", "validation", "test", "out"):
        ap.add_argument(f"--{name}", required=True)
    a = ap.parse_args(argv)

    errors = []
    classes, by_name = load_classes(a.signlist, errors)
    splits = {"train": a.train, "validation": a.validation, "test": a.test}
    ids, counts = {}, {}
    if classes:
        for split, path in splits.items():
            ids[split], counts[split] = load_labels(split, path, classes, errors)
        seen = {}
        for split in splits:
            for sid in set(ids[split]):
                if sid in seen:
                    errors.append(f"sample ID '{sid}' appears in both {seen[sid]} and {split}")
                    break
                seen[sid] = split

    # curated-table consistency
    for g, (cat, expected, _) in GLOSSES.items():
        if cat in (FOUND, CHECK) and fold(expected or "") not in by_name:
            errors.append(f"curated gloss {g}: category '{cat}' but class '{expected}' is not in the class list")
        if cat == NOT_FOUND and fold(g) in by_name:
            errors.append(f"curated gloss {g}: category 'not found' but class '{fold(g)}' exists")
    for name in CANDIDATES:
        if name not in by_name:
            errors.append(f"candidate class '{name}' is not in the class list")
    for k, (_, _, toks) in SCENARIOS.items():
        for t in toks:
            if t not in GLOSSES:
                errors.append(f"{k}: gloss {t} has no curated decision")

    if errors:
        print("Input validation failed; no output written:\n  " + "\n  ".join(errors[:50]), file=sys.stderr)
        return 2

    def n(split, cid):
        return counts[split].get(cid, 0)

    checks = []
    for split in splits:
        per_class = [n(split, cid) for cid in classes]
        checks.append({
            "split": split, "label_rows": len(ids[split]), "distinct_sample_ids": len(set(ids[split])),
            "duplicate_sample_ids": 0, "class_ids_not_in_class_list": 0,
            "classes_in_class_list": len(classes),
            "classes_with_zero_samples": sum(1 for v in per_class if v == 0),
            "min_samples_per_class_incl_zero": min(per_class), "max_samples_per_class": max(per_class),
            "distinct_signer_prefixes": len({s.split("_")[0] for s in ids[split]}),
        })

    gloss_rows = []
    for g, (cat, expected, why) in GLOSSES.items():
        used = [k for k, (_, _, toks) in SCENARIOS.items() if g in toks]
        cid = by_name[fold(expected)] if cat != NOT_FOUND else None
        tr, en = classes[cid] if cid is not None else ("", "")
        gloss_rows.append({
            "gloss": g, "used_in": ";".join(used) or "documented scenario vocabulary",
            "source": "; ".join(SCENARIOS[k][1] for k in used) or DOCUMENTED[g],
            "category": cat, "method_category": METHOD[cat],
            "autsl_class_id": "" if cid is None else cid, "autsl_tr": tr, "autsl_en": en,
            "train_samples": "" if cid is None else n("train", cid),
            "validation_samples": "" if cid is None else n("validation", cid),
            "test_samples_descriptive": "" if cid is None else n("test", cid),
            "rationale": why,
        })

    summary = []
    for k, (title, src, toks) in SCENARIOS.items():
        distinct = list(dict.fromkeys(toks))
        found = [g for g in distinct if GLOSSES[g][0] == FOUND]
        summary.append({
            "scenario": k, "title": title, "source": src,
            "numerator_found_distinct": len(found), "denominator_required_distinct": len(distinct),
            "coverage": f"{len(found)}/{len(distinct)}", "coverage_pct": f"{100 * len(found) / len(distinct):.0f}%",
            "tokens_found": sum(1 for t in toks if GLOSSES[t][0] == FOUND), "tokens_total": len(toks),
            "needs_check": ";".join(g for g in distinct if GLOSSES[g][0] == CHECK),
            "not_found": ";".join(g for g in distinct if GLOSSES[g][0] == NOT_FOUND),
            "fingerspelled_reported_separately": 0,
        })
    alld = list(dict.fromkeys(t for _, _, toks in SCENARIOS.values() for t in toks))
    summary.append({
        "scenario": "All happy paths (distinct across scenarios)", "title": "", "source": "",
        "numerator_found_distinct": sum(1 for g in alld if GLOSSES[g][0] == FOUND),
        "denominator_required_distinct": len(alld),
        "coverage": f"{sum(1 for g in alld if GLOSSES[g][0] == FOUND)}/{len(alld)}",
        "coverage_pct": f"{100 * sum(1 for g in alld if GLOSSES[g][0] == FOUND) / len(alld):.0f}%",
        "tokens_found": sum(1 for _, _, toks in SCENARIOS.values() for t in toks if GLOSSES[t][0] == FOUND),
        "tokens_total": sum(len(t) for _, _, t in SCENARIOS.values()),
        "needs_check": "", "not_found": ";".join(g for g in alld if GLOSSES[g][0] == NOT_FOUND),
        "fingerspelled_reported_separately": 0,
    })

    cand_rows = []
    for name, for_hp in CANDIDATES.items():
        cid = by_name[name]
        tr, en = classes[cid]
        cand_rows.append({"autsl_class_id": cid, "autsl_tr": tr, "autsl_en": en, "named_for": for_hp,
                          "train_samples": n("train", cid), "validation_samples": n("validation", cid),
                          "test_samples_descriptive": n("test", cid),
                          "status": "candidate named in happy-paths.md §2; not a verified synonym; adoption is a team/advisor decision"})

    os.makedirs(a.out, exist_ok=True)
    for fname, rows in (("coverage-glosses.csv", gloss_rows), ("coverage-summary.csv", summary),
                        ("candidate-classes.csv", cand_rows), ("label-checks.csv", checks)):
        with open(os.path.join(a.out, fname), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"OK: {len(classes)} classes; {len(gloss_rows)} audited glosses; 4 CSV files written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
