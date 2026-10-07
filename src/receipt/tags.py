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


def flavor_of(name, flavor):
    """0 when the name says vegetarian, 1 for meat or seafood, None otherwise (plain 蔬菜 proves nothing)."""
    if any(word in name for word in flavor["vegetarian"]):
        return 0
    if any(word in name for word in flavor["meat"]):
        return 1
    return None


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
    invoices = {}
    for row in rows:
        invoice = invoices.setdefault(row["invoice"], {
            "total": 0, "shared": False, "names": set(), "brand": brand_of(row["merchant"], brands),
            "district": None if is_remote(row["merchant"], settings["remote_sellers"]) else row.get("district")})
        invoice["total"] += row["amount"]
        if row["amount"] > 0:
            # Several portions of one item suggest the bill also covered other people.
            invoice["shared"] |= row["quantity"] >= 2 or row["name"] in invoice["names"]
            invoice["names"].add(row["name"])
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    personal = [invoice for invoice in paid if not invoice["shared"]]
    districts = Counter(invoice["district"] for invoice in paid if invoice["district"])
    chains = Counter(invoice["brand"] for invoice in paid if invoice["brand"])
    flavored, flavor_items = [], {}
    for row in valid:
        if names[row["category"]] not in flavor["categories"]:
            continue
        value = flavor_of(row["name"], flavor)
        if value is None:
            continue
        flavored.append(value)
        brand = brand_of(row["merchant"], brands)
        if brand:
            items = flavor_items.setdefault(brand, {})
            items[row["name"]] = items.get(row["name"], 0) + 1
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
        "price_level": level_of(median(invoice["total"] for invoice in personal), settings["price_levels"])
        if len(personal) >= minimum else None,
        "meat_ratio": sum(flavored) / len(flavored) if len(flavored) >= flavor["min_items"] else None,
        "flavor_items": flavor_items,
    }
    profile["tags"] = describe(profile, names, settings)
    return profile


def describe(profile, names, settings):
    counts, tags = profile["category_counts"], []
    if counts:
        total = sum(counts)
        tags += [{"dimension": "品類偏好", "text": f"常買{names[index]}（{percent(counts[index] / total)}%）"}
                 for index in profile["top_categories"]]
    tags += [{"dimension": "常消費地區", "text": area} for area in profile["areas"]]
    tags += [{"dimension": "常去品牌", "text": f"{brand}（{count} 次）"} for brand, count in profile["frequent_brands"]]
    if profile["price_level"] is not None:
        tags.append({"dimension": "消費檔次", "text": settings["price_levels"][profile["price_level"]]["label"]})
    label = flavor_label(profile["meat_ratio"], settings["flavor"])
    if label:
        tags.append({"dimension": "葷素紀錄", "text": label})
    return tags
