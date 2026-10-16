"""The match list: everyone comparable with me scored now from the stored vectors, the people past the bar on one
side, and how far from me they shop. Nothing here reads the database; the route hands it the profiles."""
import math

from ..receipt import places, similarity
from ..receipt.build import drawing_of, trait_network_data
from ..receipt.traits import signal_ids

# The farthest places.distance each scope allows; None is any distance, an unknown one included.
SCOPES = {"all": None, "district": 0, "city": 1, "region": 2}


def entries(mine, my_areas, people, model, regions):
    """Everyone who can be compared with me, in the order given: their score, its whole percentage, their home
    district closest to mine, and how far apart we shop (None when either of us has no home district)."""
    scored = []
    for person in people:
        result = similarity.compare(mine, person["vector"], model)
        if not result["comparable"]:
            continue
        areas = person["areas"]
        scored.append({"user_id": person["user_id"], "display_name": person["display_name"],
                       "score": result["score"], "percent": similarity.percent(result["score"]),
                       "area": places.closest_area(my_areas, areas, regions),
                       "distance": places.distance(my_areas, areas, regions) if my_areas and areas else None})
    return scored


def pick(entries, kind, level, match):
    """The people past the bar on one side, how many of them shop within level of me, and the first few of those.

    The bar is checked on the whole percentage the page prints, as src/web/match-filter.js does, so a card reading
    +30% is always listed. Similar goes from the highest score and opposite from the lowest; ties go by display
    name in code-point order, then by user id. A kind other than "similar" or "opposite" is a ValueError."""
    if kind not in ("similar", "opposite"):
        raise ValueError(f"kind must be 'similar' or 'opposite', not {kind!r}")
    opposite = kind == "opposite"
    line = similarity.percent(-match["opposite_score"] if opposite else match["min_score"])
    eligible = [entry for entry in entries if (entry["percent"] <= line if opposite else entry["percent"] >= line)]
    within = [entry for entry in eligible
              if level is None or (entry["distance"] is not None and entry["distance"] <= level)]
    within.sort(key=lambda entry: (entry["score"] if opposite else -entry["score"],
                                   entry["display_name"], entry["user_id"]))
    return {"eligible": len(eligible), "within": len(within), "people": within[:match["top"]]}


TOTALS = ("dot", "norm_mine", "norm_theirs", "shrink", "denominator", "score", "percent")


def breakdown(mine, theirs, model):
    """compare()'s score taken apart for the explain page: each cell's two values, weight, whether both have it, its
    product and its share of the score, then the dot product, both weighted lengths, the shrink, the denominator, the
    score and its whole percentage. The shares are compare()'s own parts, so in order they add up to its score
    exactly. When the two cannot be compared, no product, share or total is worked out at all."""
    cells = model["cells"]
    mine_values = [None] * len(cells) if mine is None else mine
    theirs_values = [None] * len(cells) if theirs is None else theirs
    shared = [a is not None and b is not None for a, b in zip(mine_values, theirs_values, strict=True)]
    result = similarity.compare(mine, theirs, model)
    comparable = result["comparable"]
    rows = []
    for index, cell in enumerate(cells):
        product = cell["weight"] * mine_values[index] * theirs_values[index] if comparable and shared[index] else None
        rows.append({"id": cell["id"], "kind": cell["kind"], "mine": mine_values[index], "theirs": theirs_values[index],
                     "weight": cell["weight"], "shared": shared[index], "product": product,
                     "part": result["parts"][index] if comparable else None})
    answer = {"comparable": comparable,
              "reason": None if comparable else "not_enough_items" if mine is None or theirs is None else "too_few_shared",
              "cells": rows,
              "shared_two_sided": sum(1 for index, cell in enumerate(cells) if shared[index] and cell["kind"] == "two_sided"),
              "min_shared_two_sided": model["min_shared_two_sided"], **dict.fromkeys(TOTALS)}
    if comparable:
        # The same sums in the same order as compare(), so the denominator here is the one its parts were divided by.
        def norm(values):
            return math.sqrt(sum(cells[index]["weight"] * values[index] ** 2 for index in range(len(cells)) if shared[index]))
        norm_mine, norm_theirs = norm(mine_values), norm(theirs_values)
        answer.update(dot=sum(row["product"] for row in rows if row["product"] is not None),
                      norm_mine=norm_mine, norm_theirs=norm_theirs, shrink=model["shrink"],
                      denominator=norm_mine * norm_theirs + model["shrink"],
                      score=result["score"], percent=similarity.percent(result["score"]))
    return answer


MONEY_UNITS = ("money", "money_month")


def without_money(settings, drawing, order):
    """drawing_of's answer with every signal measured in money, and every push of one, null. Those signals are a person's
    spending in dollars: a month's 3C spending is one purchase's price when that was the only one, and a push is
    linear in its signal inside the scale, so either would give the amount back."""
    if drawing["signals"] is None:
        return drawing
    money = {signal["id"] for trait in settings["traits"] for signal in trait["signals"] if signal["unit"] in MONEY_UNITS}
    return {**drawing,
            "signals": [None if key in money else value for key, value in zip(order, drawing["signals"], strict=True)],
            "pushes": [[None if signal["id"] in money else push for signal, push in zip(trait["signals"], pushes, strict=True)]
                       for trait, pushes in zip(settings["traits"], drawing["pushes"], strict=True)]}


def network(settings, sides):
    """The network graph's data in v1's traitNetworkData shape (build.trait_network_data), with the two people as
    mine and theirs instead of the demo friends. sides maps "mine" and "theirs" to (stored vector, traits.explain's
    answer worked out now): the graph shows the stored vector, so its dots are the explain cells' values, and a side
    with no stored vector, or no taste worked out now, is all null. On the theirs side the signals measured in money
    and their pushes are null too, so no amount of the other person is ever sent (the stored vector and the cells
    keep their values); mine shows my own."""
    order = signal_ids(settings)
    data = {key: value for key, value in trait_network_data(settings, {}, []).items() if key != "friends"}
    for side, (vector, explained) in sides.items():
        if vector is None or explained is None:
            data[side] = {"vector": None, **drawing_of(None, order)}
        else:
            drawing = drawing_of(explained, order)
            data[side] = {"vector": vector, **(without_money(settings, drawing, order) if side == "theirs" else drawing)}
    return data
