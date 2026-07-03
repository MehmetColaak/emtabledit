import pyembroidery
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox, QDoubleSpinBox


COMMAND_NAMES = {
    pyembroidery.STITCH: "STITCH",
    pyembroidery.JUMP: "JUMP",
    pyembroidery.TRIM: "TRIM",
    pyembroidery.STOP: "STOP",
    pyembroidery.COLOR_CHANGE: "COLOR_CHANGE",
    pyembroidery.END: "END",
    pyembroidery.NEEDLE_SET: "NEEDLE_SET",
    pyembroidery.SEQUIN_EJECT: "SEQUIN_EJECT",
}
NAME_TO_COMMAND = {name: cmd for cmd, name in COMMAND_NAMES.items()}

ROW_COLORS = {
    pyembroidery.JUMP: QColor(255, 244, 200),
    pyembroidery.TRIM: QColor(210, 245, 210),
    pyembroidery.COLOR_CHANGE: QColor(205, 220, 255),
    pyembroidery.STOP: QColor(255, 225, 190),
    pyembroidery.END: QColor(255, 205, 205),
}


class StitchTableModel(QAbstractTableModel):
    HEADERS = ["#", "X (mm)", "Y (mm)", "ΔX (mm)", "ΔY (mm)", "Command", "Flags"]
    EDITABLE_COLS = {1, 2, 5}

    def __init__(self, doc):
        super().__init__()
        self.doc = doc

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.doc.pattern.stitches)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in self.EDITABLE_COLS:
            base |= Qt.ItemIsEditable
        return base

    def _delta(self, row: int, axis: int) -> int:
        if row == 0:
            return 0
        stitches = self.doc.pattern.stitches
        return stitches[row][axis] - stitches[row - 1][axis]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        x, y, raw = self.doc.pattern.stitches[row]
        base_cmd = raw & pyembroidery.COMMAND_MASK

        if role in (Qt.DisplayRole, Qt.EditRole):
            if col == 0:
                return row + 1
            if col == 1:
                return round(x / 10.0, 1)
            if col == 2:
                return round(y / 10.0, 1)
            if col == 3:
                return round(self._delta(row, 0) / 10.0, 1)
            if col == 4:
                return round(self._delta(row, 1) / 10.0, 1)
            if col == 5:
                if role == Qt.EditRole:
                    return base_cmd
                return COMMAND_NAMES.get(base_cmd, f"0x{base_cmd:02X}")
            if col == 6:
                extra = raw & ~pyembroidery.COMMAND_MASK
                return f"0x{extra:X}" if extra else ""

        if role == Qt.BackgroundRole:
            return ROW_COLORS.get(base_cmd)

        return None

    def setData(self, index, value, role=Qt.EditRole) -> bool:
        if role != Qt.EditRole or not index.isValid():
            return False
        row, col = index.row(), index.column()
        try:
            if col == 1:
                self.doc.set_stitch(row, x=int(round(float(value) * 10)))
            elif col == 2:
                self.doc.set_stitch(row, y=int(round(float(value) * 10)))
            elif col == 5:
                self.doc.set_stitch(row, command=int(value))
            else:
                return False
        except (TypeError, ValueError):
            return False

        last_row = min(row + 1, self.rowCount() - 1)
        self.dataChanged.emit(self.index(row, 0), self.index(last_row, self.columnCount() - 1))
        return True

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()


class CommandDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(NAME_TO_COMMAND.keys())
        return combo

    def setEditorData(self, editor, index):
        current = index.model().data(index, Qt.EditRole)
        name = COMMAND_NAMES.get(current, "")
        pos = editor.findText(name)
        if pos >= 0:
            editor.setCurrentIndex(pos)

    def setModelData(self, editor, model, index):
        cmd = NAME_TO_COMMAND.get(editor.currentText())
        if cmd is not None:
            model.setData(index, cmd, Qt.EditRole)


class CoordinateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        box = QDoubleSpinBox(parent)
        box.setRange(-500.0, 500.0)
        box.setDecimals(1)
        box.setSingleStep(0.1)
        return box

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setValue(float(value) if value is not None else 0.0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.EditRole)
