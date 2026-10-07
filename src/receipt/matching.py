"""Score how alike two purchase profiles are and explain it; the page applies the area rule."""
import math

from .tags import flavor_label, flavor_of, percent

TASTE = ("category", "brand", "flavor", "price")
LABELS = {"category": "品類", "district": "常消費地區", "brand": "品牌", "flavor": "葷素紀錄", "price": "消費檔次"}
FLAVOR_REASONS = {"素食品項較多": "都買比較多素食品項", "葷食品項較多": "都買比較多葷食品項", "葷素品項都有": "葷素品項都有買"}


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
    return {"category": category, "district": overlap(me["district_shares"], other["district_shares"]),
            "brand": overlap(me["brand_shares"], other["brand_shares"]), "flavor": flavor, "price": price}


def weighted(parts, weights, names):
    """Weighted mean of the available parts; missing parts hand their weight to the rest."""
    available = [name for name in names if parts[name] is not None]
    weight = sum(weights[name] for name in available)
    return sum(weights[name] * parts[name] for name in available) / weight if weight else None


def ready(profile):
    """Enough data to be matched at all: category plus one more taste dimension."""
    return profile["category_counts"] is not None and (
        bool(profile["brand_shares"]) or profile["meat_ratio"] is not None or profile["price_level"] is not None)


def compare(me, other, settings):
    parts = similarities(me, other, settings)
    # Category is required, plus at least one more taste dimension, so thin data cannot score 100%.
    comparable = parts["category"] is not None and any(parts[name] is not None for name in TASTE[1:])
    return {"parts": parts, "comparable": comparable,
            "taste": weighted(parts, settings["weights"], TASTE) if comparable else None,
            "total": weighted(parts, settings["weights"], settings["weights"]) if comparable else None}


def reasons(me, other, parts, names, settings):
    found = []
    areas = [area for area in me["areas"] if area in other["areas"]]
    if areas:
        found.append(("district", f"都常在{areas[0]}消費"))
    theirs = {brand for brand, _ in other["frequent_brands"]}
    brands = [brand for brand, _ in me["frequent_brands"] if brand in theirs]
    if brands:
        found.append(("brand", f"都常去{brands[0]}"))
    categories = [index for index in me["top_categories"] if index in other["top_categories"]]
    if categories:
        found.append(("category", f"都很常買{names[categories[0]]}"))
    label = flavor_label(me["meat_ratio"], settings["flavor"])
    if label and label == flavor_label(other["meat_ratio"], settings["flavor"]):
        found.append(("flavor", FLAVOR_REASONS[label]))
    if me["price_level"] is not None and me["price_level"] == other["price_level"]:
        found.append(("price", f"消費檔次都是{settings['price_levels'][me['price_level']]['label']}"))
    weights = settings["weights"]
    found.sort(key=lambda item: -weights[item[0]] * (parts[item[0]] or 0))
    return [text for _, text in found[:3]] or ["整體消費比例相近"]


def favorite(items):
    return min(items, key=lambda name: (-items[name], name))


def differences(me, other, settings):
    flavor = settings["flavor"]
    if me["meat_ratio"] is None or other["meat_ratio"] is None:
        return []
    if abs(me["meat_ratio"] - other["meat_ratio"]) + 1e-9 < flavor["difference_at_least"]:
        return []
    theirs = {brand for brand, _ in other["frequent_brands"]}
    for brand, _ in me["frequent_brands"]:
        mine, others = me["flavor_items"].get(brand), other["flavor_items"].get(brand)
        if brand not in theirs or not mine or not others:
            continue
        a, b = favorite(mine), favorite(others)
        if flavor_of(a, flavor) != flavor_of(b, flavor):
            return [f"都常去{brand}，但點的不一樣（{a}／{b}）"]
    return ["購買紀錄不同：一位素食品項較多、一位葷食品項較多"]


def eligible(me, candidates, names, settings):
    """Everyone who could pass once an area is confirmed, best first; the page applies the final rule."""
    floor = percent(settings["thresholds"]["taste_same_area"])
    scored = [(candidate, compare(me, candidate["profile"], settings)) for candidate in candidates]
    scored = [(candidate, result) for candidate, result in scored
              if result["comparable"] and percent(result["taste"]) >= floor]
    scored.sort(key=lambda pair: (-pair[1]["total"], -pair[1]["taste"], pair[0]["name"]))
    return [{
        "name": candidate["name"], "total": percent(result["total"]), "taste": percent(result["taste"]),
        "areas": candidate["profile"]["areas"], "tags": candidate["profile"]["tags"],
        "basis": [label for name, label in LABELS.items() if result["parts"][name] is not None],
        "reasons": reasons(me, candidate["profile"], result["parts"], names, settings),
        "differences": differences(me, candidate["profile"], settings),
    } for candidate, result in scored]
