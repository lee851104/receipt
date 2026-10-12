"""Compare two taste vectors: a cosine that is shrunk toward zero when either profile is faint.

src/web/trait-similarity.js mirrors this file; both run tests/fixtures/similarity-cases.json.
"""
import math

NOT_COMPARABLE = {"comparable": False, "score": None, "parts": None}


def compare(mine, theirs, model):
    """Score from -1 to +1 and each cell's share of it; cells either side lacks are skipped, not penalised."""
    if mine is None or theirs is None:
        return dict(NOT_COMPARABLE)
    cells = model["cells"]
    shared = [index for index, (a, b) in enumerate(zip(mine, theirs)) if a is not None and b is not None]
    if sum(1 for index in shared if cells[index]["kind"] == "two_sided") < model["min_shared_two_sided"]:
        return dict(NOT_COMPARABLE)

    def norm(values):
        return math.sqrt(sum(cells[index]["weight"] * values[index] ** 2 for index in shared))

    denominator = norm(mine) * norm(theirs) + model["shrink"]
    parts = [None] * len(cells)
    for index in shared:
        parts[index] = cells[index]["weight"] * mine[index] * theirs[index] / denominator
    return {"comparable": True, "score": sum(parts[index] for index in shared), "parts": parts}


def percent(score):
    """Whole percentage, rounding halves up exactly as Math.round does in the browser."""
    return math.floor(score * 100 + 0.5)
