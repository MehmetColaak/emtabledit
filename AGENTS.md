# Agent Instructions

## Project Overview
- **Name:** emtabledit
- **Purpose:** A raw stitch-table editor for embroidery files. Open any
  format `pyembroidery` can read, edit the stitch table directly, save to
  any format `pyembroidery` can write. Personal practice tool, single user,
  no enterprise ceremony — keep it simple.
- **Files:**
    - `document.py` — `EmbroideryDocument`: pattern state, open/save_as,
      snapshot-based undo/redo. No Qt imports.
    - `table_model.py` — `QAbstractTableModel` + delegates for the stitch
      table. No document/file logic.
    - `main_window.py` — the one window: table view, menu, status bar.
    - `main.py` — entry point.
    - `tests/test_document.py` — unit tests for `document.py`.

## Key Conventions
- Units: coordinates are 1/10mm integers internally; display in mm.
- Undo/redo: snapshot-based, capped at `EmbroideryDocument.MAX_HISTORY` (20).
  Not a command-object stack — simpler and there's only one thing to get
  right (copy the stitch list before mutating).
- `save_as(path)` picks the format from the file extension via
  `pyembroidery`'s own dispatch — "export" is just "save as" with a
  different extension. Writes to `path.tmp` then renames over the target,
  so a failed write never destroys an existing file.
- Command values must be compared/set via `& pyembroidery.COMMAND_MASK` —
  the low byte is the command type, higher bits can carry encoded payload
  (e.g. needle/sequin data) that must be preserved on edit, not clobbered.
- Never hardcode raw command integers — always reference `pyembroidery`
  constants by name.
- No validation layer, no thread/preview panels, no recent-files/prefs
  persistence — deliberately cut. If pyembroidery can't write something,
  it raises and the UI shows the error.

## Commands
- **Run tests:** `python -m unittest discover tests`
- **Run app:** `python main.py`

## Environment
Two venvs exist in this repo: `emtable/` and `.venv/` (redundant — pick one
before packaging, currently both work for running tests/app).
