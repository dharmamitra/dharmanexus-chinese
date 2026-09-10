#!/usr/bin/env python3
"""Add Ask Bunkankun division notes to ZH_category-names.json as raw_metadata.

Source: Christian Wittern's "Ask Bunkankun 聞分館君" (https://ask.bunkankun.org,
CC BY-SA 4.0, https://github.com/bunkankun/ask-bkk). Each Kanripo division
(KR1a, ..., KR6v) has a note KR?/KR?x/KR?x.md with the sections "Scope and
scholarly tradition", "Important texts and text clusters", "Important
persons", "Topics" and "Timeline".

Mapping:
  * Kanripo categories (KR1a ...) are the same divisions: 1:1.
  * Taishō / Shinsan categories are volumes (T01, X55 ...), while the KR6
    divisions follow CBETA's subject classes, so one volume may spread over
    several divisions. The distribution is derived from the per-text mapping
    of add_bunkankun_summaries.py. Every division present is listed with its
    share; the full note is included for divisions holding at least
    --full-threshold of the volume's texts, and only the "Scope" section for
    divisions holding at least --scope-threshold.

raw_metadata of every category entry is regenerated from scratch; the script
also sets bunkankun_id (the main division) and bunkankun_link.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import add_bunkankun_summaries as abs_  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORY_FILE = os.path.join(HERE, "..", "ZH_category-names.json")
DIVISION_RE = re.compile(r"KR\d[a-z]")


def demote(body):
    """Normalise note headings so that the note's top level becomes ###."""
    levels = [len(m) for m in re.findall(r"^(#{1,6}) ", body, re.M)]
    if not levels:
        return body
    top = min(levels)
    shift = 3 - top
    if shift <= 0:
        return body
    return re.sub(r"^(#{1,6}) ", lambda m: "#" * (len(m.group(1)) + shift) + " ", body, flags=re.M)


def load_division_notes(ask_dir, convert):
    notes = {}
    for div in sorted(os.listdir(ask_dir)):
        if not re.fullmatch(r"KR\d", div):
            continue
        for sub in sorted(os.listdir(os.path.join(ask_dir, div))):
            path = os.path.join(ask_dir, div, sub, f"{sub}.md")
            if not DIVISION_RE.fullmatch(sub) or not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                fm, body = abs_.split_frontmatter(f.read())
            body = re.sub(r"^# .*\n", "", body.strip() + "\n", count=1, flags=re.M).strip()
            body = demote(convert(body))
            sections = re.split(r"^(?=### )", body, flags=re.M)
            scope = next((s for s in sections if s.lower().startswith("### scope")), sections[0])
            notes[sub] = {
                "title": abs_.fm_value(fm, "title"),
                "pinyin": abs_.fm_value(fm, "titlePinyin"),
                "english": abs_.fm_value(fm, "titleEnglish"),
                "body": body,
                "scope": scope.strip(),
            }
    return notes


def label(div, note):
    parts = [div, note["title"]]
    if note["pinyin"]:
        parts.append(f"*{note['pinyin']}*")
    s = " ".join(p for p in parts if p)
    return f"{s} — {note['english']}" if note["english"] else s


def source_line(div):
    return (
        f"*Source: [Ask Bunkankun 聞分館君]({abs_.SITE}) by Christian Wittern, "
        f"an AI-generated annotated catalog of the Kanseki Repository "
        f"([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)). "
        f"Full division note: [{div}]({abs_.div_url(div)}). "
        f"Read critically: the notes are machine-generated and may contain errors.*"
    )


def build_kr(cat, entry, notes):
    note = notes.get(cat)
    if not note:
        return None, None
    md = [
        f"# {entry['displayName']} ({cat})",
        "",
        f"## Division note (Ask Bunkankun 聞分館君): [{label(cat, note)}]({abs_.div_url(cat)})",
        "",
        note["body"],
        "",
        source_line(cat),
    ]
    return "\n".join(md), cat


def build_volume(cat, entry, dist, notes, full_thr, scope_thr):
    total = sum(dist.values())
    if not total:
        return None, None
    ranked = [(d, n) for d, n in dist.most_common() if d in notes]
    unmapped = sum(n for d, n in dist.items() if d not in notes)
    md = [f"# {entry['displayName']} ({cat})", ""]
    md.append("## Ask Bunkankun 聞分館君 divisions")
    md.append("")
    md.append(
        f"This volume holds {total} texts. In the Ask Bunkankun catalog, which follows "
        f"CBETA's subject classes rather than Taishō/Zokuzōkyō volumes, they belong to:"
    )
    md.append("")
    for d, n in ranked:
        md.append(f"- [{label(d, notes[d])}]({abs_.div_url(d)}): {n} texts ({n / total:.0%})")
    if unmapped:
        md.append(f"- not in the Ask Bunkankun catalog: {unmapped} texts")
    included = []
    for d, n in ranked:
        share = n / total
        if share >= full_thr:
            md += ["", f"## Division note: [{label(d, notes[d])}]({abs_.div_url(d)})", "", notes[d]["body"], "", source_line(d)]
            included.append((d, "full"))
        elif share >= scope_thr:
            md += ["", f"## Division note (scope only): [{label(d, notes[d])}]({abs_.div_url(d)})", "", notes[d]["scope"], "", source_line(d)]
            included.append((d, "scope"))
    if not included:
        md += ["", source_line(ranked[0][0])]
    return "\n".join(md), ranked[0][0], included


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask-bkk", required=True)
    ap.add_argument("--full-threshold", type=float, default=0.5)
    ap.add_argument("--scope-threshold", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    convert = abs_.load_link_converter(args.ask_bkk)
    div_notes = load_division_notes(args.ask_bkk, convert)
    text_notes = abs_.load_catalog(args.ask_bkk, "intro")
    index = abs_.build_index(text_notes)

    with open(abs_.CHINESE_FILES, encoding="utf-8") as f:
        entries = json.load(f)
    dist = defaultdict(Counter)
    seen = set()
    for e in entries:
        if e["collection"].startswith("KR") or e["textname"] in seen:
            continue
        seen.add(e["textname"])
        tid, _ = abs_.map_entry(e, text_notes, index)
        dist[e["category"]][tid[:4] if tid else "-"] += 1

    with open(CATEGORY_FILE, encoding="utf-8") as f:
        cats = json.load(f)
    stats = Counter()
    for c in cats:
        cat = c["category"]
        for k in ("raw_metadata", "bunkankun_id", "bunkankun_link"):
            c.pop(k, None)
        if cat.startswith("KR"):
            md, main_div = build_kr(cat, c, div_notes)
            kind = "kr" if md else "kr-missing"
        else:
            md, main_div, included = build_volume(cat, c, dist[cat], div_notes, args.full_threshold, args.scope_threshold) or (None, None, [])
            kind = "volume-" + ("+".join(k for _, k in included) or "list-only") if md else "volume-unmapped"
            if md and args.dry_run:
                print(cat, c["displayName"], dict(dist[cat]), included)
        stats[kind] += 1
        if md:
            c["raw_metadata"] = md
            c["bunkankun_id"] = main_div
            c["bunkankun_link"] = abs_.div_url(main_div)
    for k, n in stats.most_common():
        print(f"  {k:24s} {n}")
    total = sum(len(c.get("raw_metadata", "").encode()) for c in cats)
    print(f"raw_metadata total: {total / 1e6:.1f} MB over {len(cats)} categories")
    if args.dry_run:
        return
    with open(CATEGORY_FILE, "w", encoding="utf-8") as f:
        json.dump(cats, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"wrote {os.path.abspath(CATEGORY_FILE)}")


if __name__ == "__main__":
    sys.exit(main())
