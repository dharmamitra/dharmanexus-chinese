# dharmanexus-chinese

Chinese text data (Taishō, Manji Shinsan Zokuzōkyō, Kanripo) for DharmaNexus.

- `segments/` — one JSON file per juan-level text file.
- `ZH_files.json` — the compact catalog: one entry per segment file with
  `displayName`, `collection`, `category`, `raw_metadata` (markdown), and links.
- `ZH_collection-names.json`, `ZH_category-names.json` — display names.
- `metadata/` — one file per segment file, `metadata/<filename>-metadata.json`,
  holding the same entry as in `ZH_files.json` with an extended `raw_metadata`
  (see below) plus `bunkankun_id` and `bunkankun_link` where available. This
  folder exists so that the long summaries do not bloat `ZH_files.json`,
  which repeats text-level metadata in every juan-level entry.

## Text summaries from Ask Bunkankun 聞分館君

The `## Summary (Ask Bunkankun 聞分館君)` section in `raw_metadata` of the
`metadata/` files comes from **Ask Bunkankun 聞分館君**, Christian Wittern's
AI-generated annotated catalog of the Kanseki Repository:

- Website: <https://ask.bunkankun.org>
- Source repository: <https://github.com/bunkankun/ask-bkk>
- License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

Every summary ends with a source line linking to the full catalog entry
(which also carries bibliography, prefaces, and further notes). The catalog
notes are machine-generated and should be read critically, as the site itself
warns.

We include the introductory paragraphs of each note's "About the work"
section and its "Abstract" subsection. Obsidian wikilinks are rewritten to
links on ask.bunkankun.org (texts, divisions, persons, titles).

### Mapping

- Kanripo texts (`ZH_KR*`): matched by Kanripo id (`KR1a0001`).
- CBETA texts (`ZH_T*`, `ZH_X*`): matched via the `cbetaid` frontmatter field
  of the KR6 notes (`T01n0001`), falling back to the `source` field
  ("Taisho Tripitaka Vol. 85, No. 2920"), and to a volume-insensitive work
  number for works whose volume differs or that span several Taishō volumes
  (T0220, X0240, ...). Lettered sub-texts (T0893b/c) are only matched exactly.

Coverage as of 2026-09-10: 6899 of 6924 texts have a summary. 22 Kanripo
Daoist texts (KR5c) have only stub notes on the source side; `KR1h0018`,
`T0893b`, and `T0893c` have no matching note.

## Category-level notes

`ZH_category-names.json` carries a `raw_metadata` markdown field (plus
`bunkankun_id`, `bunkankun_link`) built from Ask Bunkankun's division notes
(`KR1a.md`, ..., `KR6v.md`: scope, important texts, persons, topics, timeline).

- Kanripo categories (KR1a, KR3e, ...) are the same divisions and get the full
  note.
- Taishō and Zokuzōkyō categories are volumes, while the KR6 divisions follow
  CBETA's subject classes. Each volume entry therefore starts with the list of
  divisions its texts fall into (with counts, derived from the per-text
  mapping), followed by the full note for any division holding at least half
  of the volume's texts and the "Scope" section for divisions holding at
  least a fifth.

The dataloader imports these records as-is, so the extra fields are harmless.

### Regenerating

```
git clone --depth 1 https://github.com/bunkankun/ask-bkk.git /path/to/ask-bkk
python3 utils/add_bunkankun_summaries.py --ask-bkk /path/to/ask-bkk
```

For the category notes:

```
python3 utils/add_bunkankun_category_notes.py --ask-bkk /path/to/ask-bkk
```

Add `--dry-run` to print mapping statistics only, `--report report.json` to
dump unmatched texts and notes shared by several of our texts, and
`--variant intro` to include only the introductory paragraphs.
