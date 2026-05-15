"""Populate raw_metadata (markdown) on every entry in ZH_files.json.

For ZH_KR* entries: copy raw_metadata from ../dharmanexus-kanripo/ZH_files.json.
For ZH_T* and ZH_X* entries: build a markdown block from CBETA metadata at
~/data/zh/cbeta-metadata/work-info/{T,X}.json.
"""

import json
import os
import re

CHINESE_FILES = "/home/sebastian/data/dharmanexus-chinese/ZH_files.json"
KANRIPO_FILES = "/home/sebastian/data/dharmanexus-kanripo/ZH_files.json"
CBETA_T = os.path.expanduser("~/data/zh/cbeta-metadata/work-info/T.json")
CBETA_X = os.path.expanduser("~/data/zh/cbeta-metadata/work-info/X.json")

CBETA_URL = "https://cbetaonline.dila.edu.tw/zh/{work_id}"

WORK_ID_RE = re.compile(r"ZH_[TX]\d+_(\d+[A-Za-z]?)")


def work_id_from_textname(textname: str) -> str | None:
    m = WORK_ID_RE.match(textname)
    if not m:
        return None
    prefix = "T" if textname.startswith("ZH_T") else "X"
    return prefix + m.group(1)


def format_date(meta: dict) -> str | None:
    tf, tt = meta.get("time_from"), meta.get("time_to")
    if tf is None and tt is None:
        return None
    if tf is not None and tt is not None and tf != tt:
        return f"{tf}–{tt}"
    return str(tf if tf is not None else tt)


def build_cbeta_markdown(work_id: str, meta: dict) -> str:
    title = meta.get("title", "")
    lines = [f"# {title}", ""]
    lines.append(f"**ID:** {work_id}")
    if meta.get("vol"):
        lines.append(f"**Volume:** {meta['vol']}")
    if meta.get("category"):
        lines.append(f"**Category:** {meta['category']}")
    if meta.get("orig_category"):
        lines.append(f"**Original Category:** {meta['orig_category']}")
    if meta.get("byline"):
        lines.append(f"**Byline:** {meta['byline']}")
    if meta.get("dynasty"):
        lines.append(f"**Dynasty:** {meta['dynasty']}")
    date = format_date(meta)
    if date is not None:
        lines.append(f"**Date:** {date}")
    if meta.get("juans"):
        lines.append(f"**Juans:** {meta['juans']}")
    lines.append(f"**CBETA:** {CBETA_URL.format(work_id=work_id)}")
    contributors = meta.get("contributors") or []
    if contributors:
        lines.append("")
        lines.append("## Contributors")
        for c in contributors:
            name = c.get("name", "")
            cid = c.get("id")
            lines.append(f"- {name} ({cid})" if cid else f"- {name}")
    return "\n".join(lines)


def main() -> None:
    with open(CHINESE_FILES, encoding="utf-8") as f:
        chinese = json.load(f)
    with open(KANRIPO_FILES, encoding="utf-8") as f:
        kanripo = json.load(f)
    with open(CBETA_T, encoding="utf-8") as f:
        t_meta = json.load(f)
    with open(CBETA_X, encoding="utf-8") as f:
        x_meta = json.load(f)

    kanripo_meta = {d["filename"]: d.get("raw_metadata") for d in kanripo}

    cbeta_md_cache: dict[str, str] = {}

    counts = {"kr": 0, "t": 0, "x": 0, "missing": 0}
    for entry in chinese:
        filename = entry.get("filename", "")
        textname = entry.get("textname", "")
        if filename.startswith("ZH_KR"):
            md = kanripo_meta.get(filename)
            if md:
                entry["raw_metadata"] = md
                counts["kr"] += 1
            else:
                counts["missing"] += 1
        elif filename.startswith("ZH_T") or filename.startswith("ZH_X"):
            work_id = work_id_from_textname(textname)
            if work_id is None:
                counts["missing"] += 1
                continue
            if work_id in cbeta_md_cache:
                entry["raw_metadata"] = cbeta_md_cache[work_id]
            else:
                table = t_meta if work_id.startswith("T") else x_meta
                meta = table.get(work_id)
                if meta is None:
                    counts["missing"] += 1
                    continue
                md = build_cbeta_markdown(work_id, meta)
                cbeta_md_cache[work_id] = md
                entry["raw_metadata"] = md
            entry["cbeta_link"] = CBETA_URL.format(work_id=work_id)
            counts["t" if work_id.startswith("T") else "x"] += 1
        else:
            counts["missing"] += 1

    with open(CHINESE_FILES, "w", encoding="utf-8") as f:
        json.dump(chinese, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(chinese)} entries. Counts: {counts}")


if __name__ == "__main__":
    main()
