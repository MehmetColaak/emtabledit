# emtabledit

A raw stitch-table editor for embroidery machine files. Open anything
[`pyembroidery`](https://github.com/EmbroidePy/pyembroidery) can read (DST,
PES, JEF, VP3, EXP, ...), edit the stitch table directly — position,
command, insert/delete rows — and save to any format `pyembroidery` can
write.

Built as a personal practice tool: single user, single file at a time, no
enterprise ceremony. See `AGENTS.md` for the architecture and conventions.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Test

```bash
python -m unittest discover tests
```

## Features

- Open/save any format pyembroidery supports (format is picked from the
  file extension — exporting to a different format is just "Save As" with
  a different extension).
- Editable stitch table: X/Y position (mm), command type, with computed
  ΔX/ΔY columns and command-based row coloring.
- Undo/redo (snapshot-based, 20 steps).
- Insert/delete stitches via right-click context menu.
- "Go to stitch #..." (Ctrl+G) and a status bar with live stitch count,
  color count, format, and pattern bounding-box size.
- Safe writes: saves go to a temp file first and rename over the target,
  so a failed write never destroys an existing file.

## License

MIT — see `LICENSE`.
