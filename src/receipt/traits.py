"""Weigh measured signals into taste traits, and line the traits up as one vector."""
import json
from datetime import date

from .signals import measure

CONFIGS = (("brands", "brands.json"), ("vocabulary", "attributes.json"), ("traits", "traits.json"), ("calendar", "calendar-2026.json"))


def load_context(root):
    """Everything the trait pipeline reads, from the project's configs folder."""
    return {key: json.loads((root / "configs" / name).read_text(encoding="utf-8")) for key, name in CONFIGS}


def dated(months):
    """Report months flattened into rows that carry their date, plus the (year, month) period they cover."""
    rows = [{**row, "date": date(month["year"], month["monthNumber"], row["day"])}
            for month in months.values() for row in month["rows"]]
    return rows, sorted((month["year"], month["monthNumber"]) for month in months.values())


def between(value, low, mid, high):
    """-1 at low, 0 at mid, +1 at high, straight lines in between and flat beyond; a falling scale works too."""
    if low > high:
        value, low, mid, high = -value, -low, -mid, -high
    if value <= mid:
        return max(-1.0, (value - mid) / (mid - low))
    return min(1.0, (value - mid) / (high - mid))


def push(value, signal, constants):
    """How far one signal moves its trait: up to 1 toward one end, or anywhere from -1 to +1 on a scale."""
    if "full" in signal:
        return signal["toward"] * min(1.0, value / signal["full"])
    low, mid, high = (constants[point] if isinstance(point, str) else point for point in signal["scale"])
    return between(value, low, mid, high)


def reaches(signal, direction):
    """Whether a signal can move its trait toward the + end (1) or the - end (-1)."""
    return "scale" in signal or signal["toward"] == direction


def trait_value(trait, measured):
    """A trait from its signals; signals that cannot be measured hand their weight to the rest."""
    signals, counts, constants = measured["signals"], measured["counts"], measured["constants"]
    if any(counts[name] < minimum for name, minimum in trait.get("requires", {}).items()):
        return None
    parts = [(signal, signals[signal["id"]]) for signal in trait["signals"] if signals[signal["id"]] is not None]
    if not parts:
        return None
    total = sum(signal["weight"] * push(value, signal, constants) for signal, value in parts)
    if trait["kind"] == "level":
        return total / sum(signal["weight"] for signal, _ in parts)
    if total == 0:
        return 0.0
    # Divide by what the available signals could reach on this side, so both ends stay reachable.
    direction = 1 if total > 0 else -1
    return total / sum(signal["weight"] for signal, _ in parts if reaches(signal, direction))


def build_vector(rows, period, context):
    """One value per trait (None where data is thin), or None when the person has too little data at all."""
    if not period:
        return None
    settings = context["traits"]
    measured = measure(rows, period, context)
    if measured["counts"]["items"] < settings["min_items"]:
        return None
    return [trait_value(trait, measured) for trait in settings["traits"]]


def similarity_model(settings):
    """What compare() needs: each cell's kind and weight, the shrink constant and the minimum overlap."""
    return {"cells": [{"id": trait["id"], "kind": trait["kind"], "weight": trait["weight"]} for trait in settings["traits"]],
            "shrink": settings["similarity"]["shrink"],
            "min_shared_two_sided": settings["similarity"]["min_shared_two_sided"]}


def typical(vectors, settings):
    """The average person: the mean of each two-sided trait over a reference population; level traits stay at 0."""
    centers = []
    for index, trait in enumerate(settings["traits"]):
        values = [vector[index] for vector in vectors if vector is not None and vector[index] is not None]
        centers.append(sum(values) / len(values) if trait["kind"] == "two_sided" and values else 0.0)
    return centers


def relative(vector, centers):
    """Each trait measured from the average person, kept within -1 and +1."""
    if vector is None:
        return None
    return [None if value is None else max(-1.0, min(1.0, value - center)) for value, center in zip(vector, centers)]


def population_vectors(people, period, context, extra=()):
    """The average person from `people`, and everyone's raw and relative vectors, people first and then `extra`.

    Names must be unique, so no one can silently replace someone else.
    """
    everyone = [*people, *extra]
    names = [person["name"] for person in everyone]
    if len(set(names)) != len(names):
        raise ValueError("Every person needs a unique name")
    raw = {person["name"]: build_vector(person["rows"], period, context) for person in everyone}
    centers = typical([raw[person["name"]] for person in people], context["traits"])
    return {"centers": centers, "raw": raw, "relative": {name: relative(vector, centers) for name, vector in raw.items()}}
