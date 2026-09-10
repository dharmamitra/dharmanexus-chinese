#!/usr/bin/env python3
"""Append Ask Bunkankun catalog summaries to raw_metadata in ZH_files.json.

Source: Christian Wittern's "Ask Bunkankun 聞分館君", an AI-generated annotated
catalog of the Kanseki Repository (https://ask.bunkankun.org, CC BY-SA 4.0),
maintained at https://github.com/bunkankun/ask-bkk.

Mapping to our catalog:
  * ZH_KR* texts: the Kanripo text id (KR1a0001) is the file name in ask-bkk.
  * ZH_T* / ZH_X* texts: ask-bkk KR6 files carry a `cbetaid:` (T01n0001) in
    their frontmatter, matched against our `old_filename` stem. Fallbacks:
    case-insensitive id, the `source:` line ("Taisho Tripitaka Vol. 85,
    No. 2920"), volume-insensitive work number, and (only when our id has no
    letter suffix) volume+letter-insensitive match (T06n0220 -> T05n0220a).

Output: one file per catalog entry, metadata/<filename>-metadata.json, holding
the ZH_files.json entry with the summary appended to raw_metadata plus
`bunkankun_id` / `bunkankun_link`. ZH_files.json itself is left untouched
(it is copied into every juan-level entry and would grow past GitHub limits).

Usage:
  add_bunkankun_summaries.py --ask-bkk DIR [--variant intro|intro+abstract]
                             [--out-dir metadata] [--dry-run] [--report r.json]
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CHINESE_FILES = os.path.join(HERE, "..", "ZH_files.json")
SITE = "https://ask.bunkankun.org"
REPO = "https://github.com/bunkankun/ask-bkk"
SECTION_HEADER = "## Summary (Ask Bunkankun 聞分館君)"

TEXT_ID_RE = re.compile(r"KR\d[a-z]\d{4}")
DIV_ID_RE = re.compile(r"KR\d[a-z]?")
CBETA_ID_RE = re.compile(r"([TX])(\d+)n(\d{4})([A-Za-z]?)")
SOURCE_RE = re.compile(
    r"(Taisho Tripitaka|Xuzangjing|Manji Daizokyo)\s+Vol\.\s*(\d+),\s*No\.\s*(\d+)([A-Za-z]?)"
)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]*?))?\]\]")


# ---------------------------------------------------------------- parsing


def split_frontmatter(text):
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", text
    return text[3:end], text[end + 4 :]


def fm_value(fm, key):
    m = re.search(rf"^{key}:[ \t]*([^\n]*)$", fm, re.M)
    return m.group(1).strip() if m else ""


def text_url(tid):
    return f"{SITE}/{tid[:3]}/{tid[:4]}/{tid}"


def div_url(did):
    if len(did) == 3:
        return f"{SITE}/{did}/"
    return f"{SITE}/{did[:3]}/{did}/"


def extract_summary(body, variant):
    """Return the descriptive summary from a catalog note body.

    intro  = paragraphs of "## About the work" before its first ### subsection
             (or, for notes without that heading, the paragraphs after the
             title block up to the first heading).
    abstract = the "### Abstract" subsection, if present.
    """
    m = re.search(r"^## About the work[ \t]*$", body, re.M)
    if m:
        region = body[m.end() :]
    else:
        h1 = re.search(r"^# .*$", body, re.M)
        if not h1:
            return ""
        region = body[h1.end() :]
        # skip the rest of the title block (english title / by-line lines)
        blank = re.search(r"\n[ \t]*\n", region)
        region = region[blank.end() :] if blank else ""
    nxt = re.search(r"^## ", region, re.M)
    if nxt:
        region = region[: nxt.start()]

    parts = re.split(r"^### ", region, flags=re.M)
    intro = parts[0].strip()
    abstract = ""
    if variant == "intro+abstract":
        for part in parts[1:]:
            head, _, rest = part.partition("\n")
            if head.strip().lower().startswith("abstract"):
                abstract = rest.strip()
                break
    out = intro
    if abstract:
        out = (out + "\n\n**Abstract**\n\n" + abstract) if out else abstract
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def make_link_converter(persons, titles):
    def convert(m):
        target, alias = m.group(1).strip(), m.group(2)
        label = (alias or target).strip()
        if TEXT_ID_RE.fullmatch(target):
            return f"[{label}]({text_url(target)})"
        if DIV_ID_RE.fullmatch(target):
            return f"[{label}]({div_url(target)})"
        if target in persons:
            return f"[{label}]({SITE}/Persons/{urllib.parse.quote(target)})"
        if target in titles:
            return f"[{label}]({SITE}/Titles/{urllib.parse.quote(target)})"
        return label

    return lambda s: WIKILINK_RE.sub(convert, s)


def load_link_converter(ask_dir):
    persons = {f[:-3] for f in os.listdir(os.path.join(ask_dir, "Persons")) if f.endswith(".md")}
    titles = {f[:-3] for f in os.listdir(os.path.join(ask_dir, "Titles")) if f.endswith(".md")}
    return make_link_converter(persons, titles)


def load_catalog(ask_dir, variant):
    convert = load_link_converter(ask_dir)
    notes = {}
    for div in sorted(os.listdir(ask_dir)):
        if not re.fullmatch(r"KR\d", div):
            continue
        for sub in sorted(os.listdir(os.path.join(ask_dir, div))):
            subdir = os.path.join(ask_dir, div, sub)
            if not os.path.isdir(subdir):
                continue
            for fn in os.listdir(subdir):
                tid = fn[:-3]
                if not fn.endswith(".md") or not TEXT_ID_RE.fullmatch(tid):
                    continue
                with open(os.path.join(subdir, fn), encoding="utf-8") as f:
                    fm, body = split_frontmatter(f.read())
                summary = extract_summary(body, variant)
                notes[tid] = {
                    "cbetaid": fm_value(fm, "cbetaid"),
                    "source": fm_value(fm, "source"),
                    "title": fm_value(fm, "title"),
                    "summary": convert(summary) if summary else "",
                }
    return notes


# ---------------------------------------------------------------- mapping


def norm_cbeta(cid):
    m = CBETA_ID_RE.fullmatch(cid.strip())
    if not m:
        return None
    canon, vol, num, letter = m.groups()
    return f"{canon}{int(vol):02d}n{num}{letter.lower()}"


def cbeta_from_source(src):
    m = SOURCE_RE.search(src)
    if not m:
        return None
    canon = "T" if m.group(1).startswith("Taisho") else "X"
    return f"{canon}{int(m.group(2)):02d}n{int(m.group(3)):04d}{m.group(4).lower()}"


def strip_vol(cid):
    m = CBETA_ID_RE.fullmatch(cid)
    return f"{m.group(1)}{m.group(3)}{m.group(4).lower()}" if m else None


def build_index(notes):
    by_cbeta, by_source, by_work, by_work_noletter = ({} for _ in range(4))
    for tid in sorted(notes):
        n = notes[tid]
        cid = norm_cbeta(n["cbetaid"]) if n["cbetaid"] else None
        if cid:
            by_cbeta.setdefault(cid, tid)
        sid = cbeta_from_source(n["source"]) if n["source"] else None
        if sid:
            by_source.setdefault(sid, tid)
        for c in (cid, sid):
            if not c:
                continue
            w = strip_vol(c)
            by_work.setdefault(w, tid)
            by_work_noletter.setdefault(w.rstrip("abcdefghijklmnopqrstuvwxyz"), tid)
    return by_cbeta, by_source, by_work, by_work_noletter


def map_entry(entry, notes, index):
    """Return (ask_bkk_text_id, stage) or (None, 'unmatched')."""
    by_cbeta, by_source, by_work, by_work_noletter = index
    if entry["collection"].startswith("KR"):
        tid = entry["textname"][3:]
        return (tid, "kr-id") if tid in notes else (None, "unmatched")
    key = norm_cbeta(entry["old_filename"].split("_")[0])
    if not key:
        return None, "unmatched"
    if key in by_cbeta:
        return by_cbeta[key], "cbetaid"
    if key in by_source:
        return by_source[key], "source"
    w = strip_vol(key)
    if w in by_work:
        return by_work[w], "novol"
    if not w[-1].isalpha() and w in by_work_noletter:
        return by_work_noletter[w], "novol-noletter"
    return None, "unmatched"


# ---------------------------------------------------------------- output


def strip_existing(raw):
    i = raw.find("\n" + SECTION_HEADER)
    return raw[:i].rstrip() if i >= 0 else raw.rstrip()


def build_section(tid, note):
    url = text_url(tid)
    lines = [SECTION_HEADER, "", note["summary"], ""]
    lines.append(
        f"*Source: [Ask Bunkankun 聞分館君]({SITE}) by Christian Wittern, "
        f"an AI-generated annotated catalog of the Kanseki Repository "
        f"([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)). "
        f"Full entry with bibliography and further notes: [{tid}]({url}). "
        f"Read critically: the notes are machine-generated and may contain errors.*"
    )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask-bkk", required=True, help="path to a clone of bunkankun/ask-bkk")
    ap.add_argument("--variant", choices=["intro", "intro+abstract"], default="intro+abstract")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "metadata"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="write mapping report (json) here")
    args = ap.parse_args()

    notes = load_catalog(args.ask_bkk, args.variant)
    index = build_index(notes)
    with open(CHINESE_FILES, encoding="utf-8") as f:
        entries = json.load(f)

    stages = Counter()
    text_stage = {}
    unmatched_texts = set()
    added_bytes = 0
    used = defaultdict(set)
    out = []
    for e in entries:
        e = dict(e)
        tid, stage = map_entry(e, notes, index)
        tkey = e["textname"]
        if tid is not None and not notes[tid]["summary"]:
            stage = "matched-empty"
            tid = None
        text_stage.setdefault(tkey, stage)
        base = strip_existing(e.get("raw_metadata") or "")
        if tid is None:
            if stage != "matched-empty":
                unmatched_texts.add(tkey)
            e["raw_metadata"] = base
        else:
            used[tid].add(tkey)
            section = build_section(tid, notes[tid])
            e["raw_metadata"] = (base + "\n\n" + section) if base else section
            e["bunkankun_id"] = tid
            e["bunkankun_link"] = text_url(tid)
            added_bytes += len(section.encode("utf-8"))
        out.append(e)

    for st in text_stage.values():
        stages[st] += 1
    print(f"texts in catalog: {len(text_stage)}")
    for st, n in stages.most_common():
        print(f"  {st:16s} {n}")
    shared = {t: sorted(v) for t, v in used.items() if len(v) > 1}
    print(f"ask-bkk notes used for >1 of our texts: {len(shared)}")
    print(f"summary text added across all files ({args.variant}): {added_bytes / 1e6:.1f} MB")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(
                {"stages": dict(stages), "unmatched": sorted(unmatched_texts), "shared_notes": shared},
                f, ensure_ascii=False, indent=1,
            )
    if args.dry_run:
        return
    os.makedirs(args.out_dir, exist_ok=True)
    for e in out:
        path = os.path.join(args.out_dir, f"{e['filename']}-metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(e, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"wrote {len(out)} files to {os.path.abspath(args.out_dir)}")


if __name__ == "__main__":
    sys.exit(main())
