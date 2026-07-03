import os
import pyembroidery


class EmbroideryDocument:
    """Single source of truth for the loaded pattern.

    Undo/redo is snapshot-based: before every edit the current stitch list
    is copied onto the undo stack. Simpler and harder to get wrong than a
    per-edit command-object stack, which is all this needs for one user
    editing one file at a time.
    """

    MAX_HISTORY = 20

    def __init__(self):
        self.pattern = pyembroidery.EmbPattern()
        self.filepath: str | None = None
        self.is_dirty: bool = False
        self._undo_stack: list[list[list[int]]] = []
        self._redo_stack: list[list[list[int]]] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # -- file I/O ----------------------------------------------------

    def open(self, path: str) -> None:
        pattern = pyembroidery.EmbPattern()
        pattern.read(path)
        self.pattern = pattern
        self.filepath = path
        self.is_dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()

    def save_as(self, path: str) -> None:
        """Write the pattern to `path`. pyembroidery picks the format from
        the file extension, so exporting to a different format is just
        saving to a path with a different extension.

        Writes to a temp file first and renames over the target so a
        failed/partial write never destroys an existing file. The temp
        file keeps the real extension (just with a ".tmp" marker inserted
        before it) since pyembroidery picks its writer from the extension.
        """
        base, ext = os.path.splitext(path)
        tmp_path = f"{base}.tmp{ext}"
        self.pattern.write(tmp_path)
        os.replace(tmp_path, path)
        self.filepath = path
        self.is_dirty = False

    # -- editing (all snapshot before mutating) -----------------------

    def _snapshot(self) -> None:
        self._undo_stack.append([list(s) for s in self.pattern.stitches])
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def set_stitch(self, index: int, x: int | None = None, y: int | None = None,
                   command: int | None = None) -> None:
        """Set position and/or command on a stitch.

        `command` is matched against `pyembroidery.COMMAND_MASK` and only
        the low bits are replaced — any encoded payload a reader may have
        packed into the higher bits (e.g. needle/sequin data) is preserved
        rather than clobbered.
        """
        self._snapshot()
        stitch = self.pattern.stitches[index]
        if x is not None:
            stitch[0] = x
        if y is not None:
            stitch[1] = y
        if command is not None:
            extra = stitch[2] & ~pyembroidery.COMMAND_MASK
            stitch[2] = extra | (command & pyembroidery.COMMAND_MASK)
        self.is_dirty = True

    def insert_stitch(self, index: int, x: int, y: int, command: int) -> None:
        self._snapshot()
        self.pattern.stitches.insert(index, [x, y, command])
        self.is_dirty = True

    def delete_stitches(self, indices: list[int]) -> None:
        self._snapshot()
        for i in sorted(set(indices), reverse=True):
            self.pattern.stitches.pop(i)
        self.is_dirty = True

    # -- undo/redo -----------------------------------------------------

    def undo(self) -> None:
        if not self.can_undo:
            return
        self._redo_stack.append([list(s) for s in self.pattern.stitches])
        self.pattern.stitches[:] = self._undo_stack.pop()
        self.is_dirty = True

    def redo(self) -> None:
        if not self.can_redo:
            return
        self._undo_stack.append([list(s) for s in self.pattern.stitches])
        self.pattern.stitches[:] = self._redo_stack.pop()
        self.is_dirty = True
