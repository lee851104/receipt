"""Summarize purchases into comparable dimensions and short tags that describe the records."""
from collections import Counter
from statistics import median

from .address import normalize_place

CONFIRMED = 10  # category 10 marks rows that still await review


def percent(value):
    """Whole percentage rounded half up, used for both display and thresholds."""
    return int(value * 100 + 0.5)


def mentions(merchant, keywords):
    name = normalize_place(merchant or "")
    return any(normalize_place(keyword) in name for keyword in keywords)


def brand_of(merchant, brands):
    """Return the chain brand whose keyword appears in the seller name, if any."""
    return next((entry["brand"] for entry in brands if mentions(merchant, entry["keywords"])), None)


def is_remote(merchant, keywords):
    """Online, delivery and utility sellers print a company address, not where the buyer was."""
    return mentions(merchant, keywords)


def meat_positions(name, words):
    for word in words:
        start = name.find(word)
        while start != -1:
            yield start
            start = name.find(word, start + 1)


def flavor_of(name, flavor):
    """0 when the name says vegetarian, 1 for meat or seafood, None otherwise (plain 蔬菜 proves nothing).

    A meat word right after 素 or 植物 names an imitation (素食雞排); any other meat word means meat was
    added, so a name that also says vegetarian (素食便當加雞腿) cannot be called either way.
    """
    prefixes = tuple(flavor["imitation_prefixes"])
    imitation = added = False
    for start in meat_positions(name, flavor["meat"]):
        if name[:start].endswith(prefixes):
            imitation = True
        else:
            added = True
    vegetarian = imitation or any(word in name for word in flavor["vegetarian"])
    if added:
        return None if vegetarian else 1
    return 0 if vegetarian else None


def flavor_label(ratio, flavor):
    if ratio is None:
        return None
    if ratio <= flavor["vegetarian_at_most"]:
        return "素食品項較多"
    if ratio >= flavor["meat_at_least"]:
        return "葷食品項較多"
    return "葷素品項都有"


def level_of(amount, levels):
    for index, level in enumerate(levels):
        if "below" not in level or amount < level["below"]:
            return index


def ranked(counter):
    """Most frequent first; ties fall back to the key so results never depend on input order."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def shares(counter):
    total = sum(counter.values())
    return {key: value / total for key, value in counter.items()}


def build_profile(rows, categories, brands, settings):
    names = [category["name"] for category in categories]
    flavor, minimum = settings["flavor"], settings["min_records"]
    # One portion per item and invoice: four hotpots on one bill count once.
    seen, valid = set(), []
    for row in rows:
        key = (row["invoice"], row["name"])
        if row["amount"] > 0 and not row["provisional"] and row["category"] < CONFIRMED and key not in seen:
            seen.add(key)
            valid.append(row)
    counts = [0] * CONFIRMED
    for row in valid:
        counts[row["category"]] += 1
    enough_items = len(valid) >= settings["category_min_items"]
    portion = names.index(settings["meal"]["portion_category"])
    food = {names.index(name) for name in settings["meal"]["food_categories"]}
    invoices = {}
    for row in rows:
        invoice = invoices.setdefault(row["invoice"], {
            "total": 0, "food": 0, "portions": 0, "brand": brand_of(row["merchant"], brands),
            "district": None if is_remote(row["merchant"], settings["remote_sellers"]) else row.get("district")})
        invoice["total"] += row["amount"]
        if not row["provisional"] and row["category"] in food:
            invoice["food"] += row["amount"]
            # Main-dish portions stand in for the number of people a bill fed.
            if row["category"] == portion and row["amount"] > 0:
                invoice["portions"] += row["quantity"]
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    meals = [invoice["food"] / invoice["portions"] for invoice in invoices.values()
             if invoice["portions"] and invoice["food"] > 0]
    districts = Counter(invoice["district"] for invoice in paid if invoice["district"])
    chains = Counter(invoice["brand"] for invoice in paid if invoice["brand"])
    judged = [flavor_of(row["name"], flavor) for row in valid if names[row["category"]] in flavor["categories"]]
    flavored = [value for value in judged if value is not None]
    known_area = sum(districts.values()) >= minimum
    profile = {
        "item_count": len(valid),
        "category_counts": counts if enough_items else None,
        "top_categories": [index for index, count in ranked(dict(enumerate(counts))) if count][:settings["category_top"]]
        if enough_items else [],
        "district_shares": shares(districts) if known_area else {},
        "areas": [district for district, count in ranked(districts)
                  if count >= settings["district_min_invoices"]][:settings["district_top"]] if known_area else [],
        "brand_shares": shares(chains) if sum(chains.values()) >= minimum else {},
        "frequent_brands": [(brand, count) for brand, count in ranked(chains) if count >= settings["brand_min_invoices"]],
        "price_level": level_of(median(meals), settings["price_levels"]) if len(meals) >= minimum else None,
        "meat_ratio": sum(flavored) / len(flavored) if len(flavored) >= flavor["min_items"] else None,
    }
    profile["tags"] = describe(profile, names, settings)
    return profile


def describe(profile, names, settings):
    """Tags in display order; two tags of one dimension are the same when their keys match."""
    counts, tags = profile["category_counts"], []
    if counts:
        total = sum(counts)
        tags += [{"dimension": "品類偏好", "key": names[index], "text": f"常買{names[index]}（{percent(counts[index] / total)}%）"}
                 for index in profile["top_categories"]]
    tags += [{"dimension": "常消費地區", "key": area, "text": area} for area in profile["areas"]]
    tags += [{"dimension": "常去品牌", "key": brand, "text": f"{brand}（{count} 次）"}
             for brand, count in profile["frequent_brands"]]
    if profile["price_level"] is not None:
        level = settings["price_levels"][profile["price_level"]]["label"]
        tags.append({"dimension": "消費檔次", "key": level, "text": level})
    label = flavor_label(profile["meat_ratio"], settings["flavor"])
    if label:
        tags.append({"dimension": "葷素紀錄", "key": label, "text": label})
    return tags
