"""Read what one purchase line says about itself: traits of the item, and the kind of shop it came from."""
import re

from .address import normalize_place

# Category indices from configs/report.json.
MEAL, DRINK, DESSERT, FRESH, SPORT, DAILY, TECH = 0, 1, 2, 3, 4, 8, 9
FOOD = {MEAL, DRINK, DESSERT, FRESH}
GOODS = {4, 5, 6, 7, 8, 9}  # confirmed categories that are not food
GENERAL = "一般店家"


def fold(text):
    """Compare without spacing, with 台 written as 臺, and ignoring letter case."""
    return normalize_place(text or "").casefold()


def has(text, words):
    folded = fold(text)
    return any(fold(word) in folded for word in words)


def channel_of(merchant, brands, vocabulary):
    """A listed brand decides first, then words in the seller name; anything else is an ordinary shop."""
    for entry in brands:
        if has(merchant, entry["keywords"]):
            return entry["channel"]
    for entry in vocabulary["seller_channels"]:
        if has(merchant, entry["keywords"]):
            return entry["channel"]
    return GENERAL


def sugar_of(name, channel, vocabulary):
    """0 for unsweetened through 1 for full sugar; None when the name gives no hint."""
    for word, sugar in vocabulary["sugar_words"]:
        if has(name, [word]):
            return sugar
    for entry in vocabulary["sugar_defaults"]:
        if has(name, entry["keywords"]):
            return entry["sugar"]
    # Tea shops sweeten fully unless told otherwise.
    return 1 if channel == "手搖" else None


def species_of(name, vocabulary):
    if has(name, vocabulary["cat"]):
        return "cat"
    if has(name, vocabulary["dog"]):
        return "dog"
    return None


def fun_of(name, merchant, vocabulary):
    return next((kind for kind, words in vocabulary["fun"].items() if has(name, words) or has(merchant, words)), None)


def describe(row, channel, vocabulary):
    """Every question the signals ask about one line, answered once."""
    name, category = row["name"], row["category"]
    goods = category in GOODS
    return {
        "food": category in FOOD,
        "clearance": category in FOOD and has(name, vocabulary["clearance"]),
        "sugar": sugar_of(name, channel, vocabulary) if category == DRINK else None,
        "quick": category == MEAL and has(name, vocabulary["quick"]),
        "cooking": category == FRESH and not has(name, vocabulary["fruit"]),
        "kitchen": category in (FRESH, DAILY) and has(name, vocabulary["kitchen"]),
        "sport_supply": has(name, vocabulary["sport_supply"]),
        "sport_gear": goods and has(name, vocabulary["sport_gear"]),
        "car_care": goods and has(name, vocabulary["car_care"]),
        "bulk": has(name, vocabulary["bulk"]) or bool(re.search(r"\d+入", fold(name))) or row["quantity"] >= 3,
        "home": goods and has(name, vocabulary["home"]),
        "stationery": goods and has(name, vocabulary["stationery"]),
        "fun": fun_of(name, row["merchant"], vocabulary),
        "pet_food": has(name, vocabulary["pet_food"]),
        "pet_supply": has(name, vocabulary["pet_supply"]),
        "species": species_of(name, vocabulary),
        "alcohol": has(name, vocabulary["alcohol"]) and not has(name, vocabulary["not_alcohol"]),
    }
