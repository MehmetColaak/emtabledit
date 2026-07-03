import os
import pyembroidery
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QStatusBar, QTableView,
    QHeaderView, QMenu, QAbstractItemView, QInputDialog,
)

from document import EmbroideryDocument
from table_model import StitchTableModel, CommandDelegate, CoordinateDelegate


def _format_filter(capability: str) -> str:
    """Build a QFileDialog filter string from pyembroidery's own format list
    so it never drifts out of sync with what pyembroidery can actually do."""
    fmts = list(pyembroidery.supported_formats())
    exts = sorted({f["extension"] for f in fmts if f.get(capability)})
    return "Embroidery Files (" + " ".join(f"*.{e}" for e in exts) + ")"


READ_FILTER = _format_filter("reader")
WRITE_FILTER = _format_filter("writer")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.doc = EmbroideryDocument()
        self.resize(900, 600)

        self.model = StitchTableModel(self.doc)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(1, CoordinateDelegate(self.table))
        self.table.setItemDelegateForColumn(2, CoordinateDelegate(self.table))
        self.table.setItemDelegateForColumn(5, CommandDelegate(self.table))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.setCentralWidget(self.table)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._build_menu()
        self._build_shortcuts()
        self._refresh()

    # -- menu / shortcuts ------------------------------------------------

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Open...", self.open_file)
        file_menu.addAction("Save As...", self.save_as_file)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.undo_action = edit_menu.addAction("Undo", self.undo)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_action = edit_menu.addAction("Redo", self.redo)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Go to stitch #...", self.go_to_stitch).setShortcut(QKeySequence("Ctrl+G"))

    def _build_shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self.redo)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, activated=self.delete_selected_rows)

    # -- context menu / row editing ---------------------------------------

    def _selected_rows(self) -> list[int]:
        return sorted({idx.row() for idx in self.table.selectedIndexes()})

    def _show_context_menu(self, pos):
        rows = self._selected_rows()

        menu = QMenu(self)
        insert_stitch = menu.addAction("Insert STITCH above")
        insert_jump = menu.addAction("Insert JUMP above")
        insert_trim = menu.addAction("Insert TRIM above")
        insert_color = menu.addAction("Insert COLOR_CHANGE above")
        menu.addSeparator()
        delete_rows = menu.addAction("Delete selected row(s)")
        menu.addSeparator()
        goto = menu.addAction("Go to stitch #...")

        for action in (insert_stitch, insert_jump, insert_trim, insert_color, delete_rows):
            action.setEnabled(bool(rows))

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action is None:
            return

        command_by_action = {
            insert_stitch: pyembroidery.STITCH,
            insert_jump: pyembroidery.JUMP,
            insert_trim: pyembroidery.TRIM,
            insert_color: pyembroidery.COLOR_CHANGE,
        }
        if action in command_by_action:
            self._insert_row(rows[0], command_by_action[action])
        elif action is delete_rows:
            self.doc.delete_stitches(rows)
            self._refresh()
        elif action is goto:
            self.go_to_stitch()

    def go_to_stitch(self):
        row_count = self.model.rowCount()
        if row_count == 0:
            return
        current_row = self.table.currentIndex().row()
        stitch_num, ok = QInputDialog.getInt(
            self, "Go to Stitch", "Stitch #:",
            value=max(current_row, 0) + 1, minValue=1, maxValue=row_count,
        )
        if not ok:
            return
        index = self.model.index(stitch_num - 1, 0)
        self.table.setCurrentIndex(index)
        self.table.selectRow(stitch_num - 1)
        self.table.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _insert_row(self, row: int, command: int):
        if self.doc.pattern.stitches:
            x, y = self.doc.pattern.stitches[row][0], self.doc.pattern.stitches[row][1]
        else:
            x, y = 0, 0
        self.doc.insert_stitch(row, x, y, command)
        self._refresh()

    def delete_selected_rows(self):
        rows = self._selected_rows()
        if rows:
            self.doc.delete_stitches(rows)
            self._refresh()

    # -- file actions ------------------------------------------------------

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", READ_FILTER)
        if not path:
            return
        try:
            self.doc.open(path)
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return
        self._refresh()

    def save_as_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "", WRITE_FILTER)
        if not path:
            return
        try:
            self.doc.save_as(path)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return
        self._refresh()

    def undo(self):
        self.doc.undo()
        self._refresh()

    def redo(self):
        self.doc.redo()
        self._refresh()

    # -- status / lifecycle -------------------------------------------------

    def _refresh(self):
        self.model.refresh()
        name = os.path.basename(self.doc.filepath) if self.doc.filepath else "Untitled"
        dirty = "*" if self.doc.is_dirty else ""
        self.status.showMessage(f"{name}{dirty}   |   {self._stats_text()}")
        self.setWindowTitle(f"emtabledit — {name}{dirty}")
        self.undo_action.setEnabled(self.doc.can_undo)
        self.redo_action.setEnabled(self.doc.can_redo)

    def _stats_text(self) -> str:
        stitches = self.doc.pattern.stitches
        count = len(stitches)
        colors = len(self.doc.pattern.threadlist)
        fmt = os.path.splitext(self.doc.filepath)[1][1:].upper() if self.doc.filepath else "-"

        if count:
            xs = [s[0] for s in stitches]
            ys = [s[1] for s in stitches]
            size = f"{(max(xs) - min(xs)) / 10.0:.1f}x{(max(ys) - min(ys)) / 10.0:.1f} mm"
        else:
            size = "0x0 mm"

        return f"Stitches: {count}   Colors: {colors}   Format: {fmt}   Size: {size}"

    def closeEvent(self, event):
        if self.doc.is_dirty:
            answer = QMessageBox.question(
                self, "Unsaved changes", "Discard unsaved changes and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
