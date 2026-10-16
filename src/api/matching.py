"""The match list: everyone comparable with me scored now from the stored vectors, the people past the bar on one
side, and how far from me they shop. Nothing here reads the database; the route hands it the profiles."""
from ..receipt import places, similarity

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
