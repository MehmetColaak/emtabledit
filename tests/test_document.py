import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyembroidery
from document import EmbroideryDocument


class TestEmbroideryDocument(unittest.TestCase):
    def setUp(self):
        self.doc = EmbroideryDocument()
        self.doc.pattern.stitches = [
            [0, 0, pyembroidery.STITCH],
            [10, 10, pyembroidery.STITCH],
            [20, 20, pyembroidery.END],
        ]

    def test_set_stitch_position(self):
        self.doc.set_stitch(0, x=50, y=60)
        self.assertEqual(self.doc.pattern.stitches[0][:2], [50, 60])
        self.assertTrue(self.doc.is_dirty)

    def test_set_stitch_command_preserves_extra_bits(self):
        # simulate a command with encoded extra data in the high bits
        self.doc.pattern.stitches[1][2] = pyembroidery.STITCH | (5 << 8)
        self.doc.set_stitch(1, command=pyembroidery.JUMP)
        raw = self.doc.pattern.stitches[1][2]
        self.assertEqual(raw & pyembroidery.COMMAND_MASK, pyembroidery.JUMP)
        self.assertEqual(raw & ~pyembroidery.COMMAND_MASK, 5 << 8)

    def test_insert_and_delete(self):
        self.doc.insert_stitch(1, 5, 5, pyembroidery.JUMP)
        self.assertEqual(len(self.doc.pattern.stitches), 4)
        self.assertEqual(self.doc.pattern.stitches[1], [5, 5, pyembroidery.JUMP])

        self.doc.delete_stitches([0, 1])
        self.assertEqual(len(self.doc.pattern.stitches), 2)

    def test_undo_redo_sequential(self):
        original = [list(s) for s in self.doc.pattern.stitches]
        for i in range(10):
            self.doc.set_stitch(0, x=100 + i, y=200 + i)
        self.assertEqual(self.doc.pattern.stitches[0][:2], [109, 209])

        for _ in range(10):
            self.doc.undo()
        self.assertEqual(self.doc.pattern.stitches, original)

        for _ in range(10):
            self.doc.redo()
        self.assertEqual(self.doc.pattern.stitches[0][:2], [109, 209])

    def test_undo_redo_across_insert_delete(self):
        self.doc.insert_stitch(0, 1, 1, pyembroidery.JUMP)
        self.doc.delete_stitches([2])
        self.assertEqual(len(self.doc.pattern.stitches), 3)

        self.doc.undo()  # undoes delete
        self.assertEqual(len(self.doc.pattern.stitches), 4)
        self.doc.undo()  # undoes insert
        self.assertEqual(len(self.doc.pattern.stitches), 3)
        self.assertFalse(self.doc.can_undo)

    def test_history_capped(self):
        for i in range(EmbroideryDocument.MAX_HISTORY + 5):
            self.doc.set_stitch(0, x=i)
        self.assertEqual(len(self.doc._undo_stack), EmbroideryDocument.MAX_HISTORY)

    def test_save_as_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.dst")
            self.doc.save_as(path)
            self.assertTrue(os.path.exists(path))
            self.assertFalse(os.path.exists(path + ".tmp"))

            reopened = EmbroideryDocument()
            reopened.open(path)
            self.assertEqual(len(reopened.pattern.stitches), 3)

    def test_save_as_different_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst_path = os.path.join(tmp, "out.dst")
            pes_path = os.path.join(tmp, "out.pes")
            self.doc.save_as(dst_path)
            self.doc.save_as(pes_path)
            self.assertTrue(os.path.exists(pes_path))


if __name__ == "__main__":
    unittest.main()
