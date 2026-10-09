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


def trait_parts(trait, measured):
    """A trait and how far each of its signals pushed it, in the trait's signal order.

    Signals that cannot be measured push nothing (None) and hand their weight to the rest; a trait
    without enough data is None, and so is every push.
    """
    signals, counts, constants = measured["signals"], measured["counts"], measured["constants"]
    nothing = (None, [None] * len(trait["signals"]))
    if any(counts[name] < minimum for name, minimum in trait.get("requires", {}).items()):
        return nothing
    raw = [None if signals[signal["id"]] is None else signal["weight"] * push(signals[signal["id"]], signal, constants)
           for signal in trait["signals"]]
    available = [signal for signal, value in zip(trait["signals"], raw) if value is not None]
    if not available:
        return nothing
    total = sum(value for value in raw if value is not None)
    if trait["kind"] == "level":
        scale = sum(signal["weight"] for signal in available)
    elif total == 0:
        return 0.0, raw
    else:
        # Divide by what the available signals could reach on this side, so both ends stay reachable.
        direction = 1 if total > 0 else -1
        scale = sum(signal["weight"] for signal in available if reaches(signal, direction))
    return total / scale, [None if value is None else value / scale for value in raw]


def trait_value(trait, measured):
    """A trait from its signals; signals that cannot be measured hand their weight to the rest."""
    return trait_parts(trait, measured)[0]


def explain(rows, period, context):
    """One person's taste: the vector, each signal's push on each trait, and the measured signals.

    None when the person has too little data at all.
    """
    if not period:
        return None
    settings = context["traits"]
    measured = measure(rows, period, context)
    if measured["counts"]["items"] < settings["min_items"]:
        return None
    parts = [trait_parts(trait, measured) for trait in settings["traits"]]
    return {"vector": [value for value, _ in parts], "pushes": [pushes for _, pushes in parts],
            "signals": measured["signals"]}


def build_vector(rows, period, context):
    """One value per trait (None where data is thin), or None when the person has too little data at all."""
    explained = explain(rows, period, context)
    return None if explained is None else explained["vector"]


def population(people, period, context):
    """Everyone's explained taste by name, None for those with too little data; names must be unique."""
    names = [person["name"] for person in people]
    if len(set(names)) != len(names):
        raise ValueError("Every person needs a unique name")
    return {person["name"]: explain(person["rows"], period, context) for person in people}


def signal_ids(settings):
    """Every signal once, in the order it first appears among the traits; embedded signal lists follow it."""
    ids = []
    for trait in settings["traits"]:
        ids += [signal["id"] for signal in trait["signals"] if signal["id"] not in ids]
    return ids


def similarity_model(settings):
    """What compare() needs: each cell's kind and weight, the shrink constant and the minimum overlap."""
    return {"cells": [{"id": trait["id"], "kind": trait["kind"], "weight": trait["weight"]} for trait in settings["traits"]],
            "shrink": settings["similarity"]["shrink"],
            "min_shared_two_sided": settings["similarity"]["min_shared_two_sided"]}
