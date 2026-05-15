"""Add folio-level cbeta_link to each segment in T and X segment JSON files.

URL format: https://cbetaonline.dila.edu.tw/zh/<COL><VOL>n<WORK>_p<PAGE><REG><LINE>
e.g. segmentnr ZH_T01_0001_010:0059b11_0 -> .../zh/T01n0001_p0059b11

KR segments are skipped (not in CBETA).
"""

import glob
import json
import os
import re

SEGMENTS_DIR = "/home/sebastian/data/dharmanexus-chinese/segments"
CBETA_URL = "https://cbetaonline.dila.edu.tw/zh/{ref}"

FILENAME_RE = re.compile(r"^ZH_([TX])(\d+)_(\d+[A-Za-z]?)_\d+[a-z]?$")
FOLIO_RE = re.compile(r"(\d{4}[a-z]\d{2})")


def cbeta_ref(filename: str, segmentnr: str) -> str | None:
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    col, vol, work = m.group(1), m.group(2), m.group(3)
    if ":" not in segmentnr:
        return None
    folio_part = segmentnr.split(":", 1)[1]
    fm = FOLIO_RE.search(folio_part)
    if not fm:
        return None
    return f"{col}{vol}n{work}_p{fm.group(1)}"


def main() -> None:
    files = sorted(glob.glob(os.path.join(SEGMENTS_DIR, "ZH_T*.json"))) + sorted(
        glob.glob(os.path.join(SEGMENTS_DIR, "ZH_X*.json"))
    )
    total_files = 0
    total_segs = 0
    linked_segs = 0
    skipped_segs = 0
    for path in files:
        filename = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            segments = json.load(f)
        changed = False
        for seg in segments:
            total_segs += 1
            segnr = seg.get("segmentnr", "")
            ref = cbeta_ref(filename, segnr)
            if ref is None:
                skipped_segs += 1
                continue
            link = CBETA_URL.format(ref=ref)
            if seg.get("cbeta_link") != link:
                seg["cbeta_link"] = link
                changed = True
            linked_segs += 1
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(segments, f, ensure_ascii=False, indent=2)
        total_files += 1
    print(
        f"files: {total_files}, segments: {total_segs}, "
        f"linked: {linked_segs}, skipped: {skipped_segs}"
    )


if __name__ == "__main__":
    main()
