"""Score how alike two purchase profiles are, pick the tags that show it, and measure how far apart they shop."""
import math

from .tags import percent

TASTE = ("category", "brand", "flavor", "price")
# The other person's tags are checked one dimension at a time, in these orders. Areas never explain a match:
# they come from seller addresses, so they only matter once someone chooses a distance on the page.
LIKE = ("常去品牌", "葷素紀錄", "消費檔次", "品類偏好")
UNLIKE = ("葷素紀錄", "消費檔次", "常去品牌", "品類偏好")
LABELED = ("葷素紀錄", "消費檔次")  # a label I lack cannot differ from theirs


def overlap(a, b):
    """Histogram intersection of two share maps, or None when either side lacks data."""
    if not a or not b:
        return None
    return sum(min(value, b.get(key, 0)) for key, value in a.items())


def similarities(me, other, settings):
    mine, theirs = me["category_counts"], other["category_counts"]
    category = None
    if mine and theirs:
        norm = math.hypot(*mine) * math.hypot(*theirs)
        category = min(1.0, sum(x * y for x, y in zip(mine, theirs)) / norm) if norm else None
    span = len(settings["price_levels"]) - 1
    price = None
    if me["price_level"] is not None and other["price_level"] is not None:
        price = 1 - abs(me["price_level"] - other["price_level"]) / span if span else 1.0
    flavor = None
    if me["meat_ratio"] is not None and other["meat_ratio"] is not None:
        flavor = 1 - abs(me["meat_ratio"] - other["meat_ratio"])
    return {"category": category, "brand": overlap(me["brand_shares"], other["brand_shares"]),
            "flavor": flavor, "price": price}


def weighted(parts, weights):
    """Weighted mean of the available parts; missing parts hand their weight to the rest."""
    available = [name for name in weights if parts[name] is not None]
    weight = sum(weights[name] for name in available)
    return sum(weights[name] * parts[name] for name in available) / weight if weight else None


def ready(profile):
    """Enough data to be matched at all: category plus one more dimension."""
    return profile["category_counts"] is not None and (
        bool(profile["brand_shares"]) or profile["meat_ratio"] is not None or profile["price_level"] is not None)


def compare(me, other, settings):
    parts = similarities(me, other, settings)
    # Category is required, plus at least one more dimension, so thin data cannot score 100%.
    comparable = parts["category"] is not None and any(parts[name] is not None for name in TASTE[1:])
    return {"parts": parts, "comparable": comparable,
            "score": weighted(parts, settings["weights"]) if comparable else None}


def place_distance(a, b, regions):
    """0 for the same district, 1 for the same city or county, 2 for the same region, 3 otherwise."""
    if a == b:
        return 0
    if a[:3] == b[:3]:
        return 1
    region = {city: name for name, cities in regions.items() for city in cities}
    return 2 if region.get(a[:3]) is not None and region.get(a[:3]) == region.get(b[:3]) else 3


def distance(mine, theirs, regions):
    """The closest pair of frequent areas; 3 when either side has none."""
    return min((place_distance(a, b, regions) for a in mine for b in theirs), default=3)


def shown(tag):
    return {"dimension": tag["dimension"], "text": tag["text"]}


def most_alike(me, other):
    """The other person's first tag that I share, checked in LIKE order."""
    mine = {(tag["dimension"], tag["key"]) for tag in me["tags"]}
    return next((shown(tag) for dimension in LIKE for tag in other["tags"]
                 if tag["dimension"] == dimension and (dimension, tag["key"]) in mine), None)


def least_alike(me, other):
    """The other person's first tag that I do not share, checked in UNLIKE order."""
    mine = {(tag["dimension"], tag["key"]) for tag in me["tags"]}
    have = {tag["dimension"] for tag in me["tags"]}
    return next((shown(tag) for dimension in UNLIKE for tag in other["tags"]
                 if tag["dimension"] == dimension and (dimension, tag["key"]) not in mine
                 and (dimension not in LABELED or dimension in have)), None)


def eligible(me, candidates, settings):
    """Everyone at or above the nearby threshold, best first; the page decides who is shown."""
    floor = percent(settings["thresholds"]["nearby"])
    scored = []
    for candidate in candidates:
        result = compare(me, candidate["profile"], settings)
        if result["comparable"] and percent(result["score"]) >= floor:
            scored.append((percent(result["score"]), candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    return [{
        "name": candidate["name"], "score": score,
        "distance": distance(me["areas"], candidate["profile"]["areas"], settings["regions"]),
        "like": most_alike(me, candidate["profile"]), "unlike": least_alike(me, candidate["profile"]),
        "counts": candidate["profile"]["category_counts"],
    } for score, candidate in scored]
