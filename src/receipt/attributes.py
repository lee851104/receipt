"""Read what one purchase line says about itself: traits of the item, and the kind of shop it came from."""
import re

from .address import normalize_place

# Category indices from configs/report.json.
MEAL, DRINK, DESSERT, FRESH, SPORT, DAILY, TECH = 0, 1, 2, 3, 4, 8, 9
FOOD = {MEAL, DRINK, DESSERT, FRESH}
GOODS = {4, 5, 6, 7, 8, 9}  # confirmed categories that are not food
GENERAL = "一般店家"
# The categories a model's question is asked about; outside them the answer is a known no. Questions missing here are
# asked about every category.
ASKED_ABOUT = {"clearance": FOOD, "quick": {MEAL}, "cooking": {FRESH}, "kitchen": {FRESH, DAILY},
               "sport_gear": GOODS, "car_care": GOODS, "home": GOODS, "stationery": GOODS}
# The model's kinds of fun, written the way the vocabulary and the pages write them.
FUN_WORDS = {"movie": "電影", "singing": "唱歌", "show": "展演", "game": "遊樂"}


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


def asked(question, category):
    """Whether a model's question is asked about an item of this category."""
    return category in ASKED_ABOUT.get(question, {category})


def fun_of_model(kind):
    """The kind of fun a model's answer names, in Chinese, or None when it names none of the four. Both spellings are
    taken: describe_items hands over the Chinese words (task 4.3), the experiment's own answers are the English ones."""
    return FUN_WORDS.get(kind, kind if kind in FUN_WORDS.values() else None)


def from_model(row, channel, fields, vocabulary):
    """The answers of describe(), from a model's attributes for the name. None means unknown, never no.

    A name still waiting for the model (fields is None) answers like a model that knows nothing. The category comes
    from the classifier, so a question outside its categories is a known no (False), inside them it is the model's
    answer, and the model's None stays None.
    """
    fields = fields or {}
    name, category = row["name"], row["category"]

    def answer(question):
        return fields.get(question) if asked(question, category) else False

    sugar = fields.get("sugar")
    species = fields.get("species")
    return {
        "food": category in FOOD,
        "clearance": answer("clearance"),
        # Without the model's answer a drink is as sweet as its name or its shop suggests.
        "sugar": (sugar_of(name, channel, vocabulary) if sugar is None else sugar) if category == DRINK else None,
        "quick": answer("quick"),
        "cooking": answer("cooking"),
        "kitchen": answer("kitchen"),
        "sport_supply": answer("sport_supply"),
        "sport_gear": answer("sport_gear"),
        "car_care": answer("car_care"),
        # Three of a kind are bulk: the quantity is on the invoice, where the model cannot see it.
        "bulk": True if row["quantity"] >= 3 else answer("bulk"),
        "home": answer("home"),
        "stationery": answer("stationery"),
        # No kind of fun from the model: the shop's own words decide, never the name (an empty name has none).
        "fun": fun_of_model(fields.get("fun")) or fun_of("", row["merchant"], vocabulary),
        "pet_food": answer("pet_food"),
        "pet_supply": answer("pet_supply"),
        "species": species if species in ("cat", "dog") else None,
        "alcohol": answer("alcohol"),
    }
