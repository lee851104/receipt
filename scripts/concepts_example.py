"""Print a fictional teaching example in the explanation API's numeric shape.

This is a local calculation reference, not an HTTP endpoint or database seed.
"""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.receipt.similarity import compare, percent
from src.receipt.traits import similarity_model


def example():
    settings = json.loads((ROOT / "configs/traits.json").read_text(encoding="utf-8"))
    model = similarity_model(settings)
    a = {"spend": .6, "meals": .8, "motive": .2, "cooking": -.6, "sweet": -.8}
    b = {"spend": .8, "meals": .6, "motive": -.2, "cooking": -.8, "sweet": -.6}
    mine = [a.get(t["id"]) for t in settings["traits"]]
    theirs = [b.get(t["id"]) for t in settings["traits"]]
    result = compare(mine, theirs, model)
    cells = []
    for i, t in enumerate(settings["traits"]):
        shared = mine[i] is not None and theirs[i] is not None
        cells.append({"id": t["id"], "name": t["name"], "kind": t["kind"],
                      "mine": mine[i], "theirs": theirs[i], "weight": model["cells"][i]["weight"],
                      "shared": shared, "product": model["cells"][i]["weight"] * mine[i] * theirs[i] if shared else None,
                      "part": result["parts"][i]})
    def norm(side):
        return math.sqrt(sum(c["weight"] * c[side] ** 2 for c in cells if c["shared"]))
    return {"example_only": True, "display_name": "虛構乙", "comparable": result["comparable"], "reason": None,
            "cells": cells, "shared_two_sided": 5, "min_shared_two_sided": model["min_shared_two_sided"],
            "dot": sum(c["product"] for c in cells if c["shared"]), "norm_mine": norm("mine"),
            "norm_theirs": norm("theirs"), "shrink": model["shrink"],
            "denominator": norm("mine") * norm("theirs") + model["shrink"],
            "score": result["score"], "percent": percent(result["score"])}


if __name__ == "__main__":
    print(json.dumps(example(), ensure_ascii=False, indent=2))
