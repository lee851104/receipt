"""Reference shape validation prevents partial probability comparison."""
import copy
import unittest
from scripts.verify_category_service import validate_reference, PROBES, MODEL_SHA256, probe_fingerprint

class ReferenceTests(unittest.TestCase):
    def test_complete_reference_and_malformed_shapes(self):
        reference = dict(model_sha256=MODEL_SHA256, probe_sha256=probe_fingerprint(),
                         categories=[0]*len(PROBES), probabilities=[[.1]*10 for _ in PROBES])
        validate_reference(reference)
        for change in (
            lambda r: r["probabilities"][0].pop(),
            lambda r: r["probabilities"].pop(),
            lambda r: r["categories"].pop(),
            lambda r: r["categories"].__setitem__(0, True),
            lambda r: r["categories"].__setitem__(0, 10),
            lambda r: r["probabilities"][0].__setitem__(0, float("nan")),
            lambda r: r["probabilities"][0].__setitem__(0, True),
            lambda r: r["probabilities"][0].__setitem__(0, -1),
            lambda r: r["probabilities"][0].__setitem__(0, .5),
            lambda r: r.__setitem__("model_sha256", "wrong"),
            lambda r: r.__setitem__("probe_sha256", "wrong"),
        ):
            broken = copy.deepcopy(reference)
            change(broken)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_reference(broken)
