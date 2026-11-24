import unittest
from goosecad.document.native import Feature, NativeDocument

class UIContractTests(unittest.TestCase):
    def test_parameter_and_history_metadata(self):
        doc = NativeDocument({"x": 2, "y": 3, "z": 4},
                             (Feature("box", "box", ("x", "y", "z")),))
        detached = doc.parameter_values()
        detached["x"] = 100
        self.assertEqual(doc.parameter_values()["x"], 2)
        self.assertEqual(doc.features[0].id, "box")
        self.assertEqual(doc.history_depths, (0, 0))
        doc.edit({"x": 6})
        self.assertEqual(doc.history_depths, (1, 0))
        doc.undo()
        self.assertEqual(doc.history_depths, (0, 1))
        doc.redo()
        self.assertEqual(doc.history_depths, (1, 0))
