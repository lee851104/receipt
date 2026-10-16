"""Measure one person's purchases: the shares, monthly counts and medians the taste traits weigh."""
from collections import Counter
from datetime import date, timedelta
from statistics import mean, median

from .attributes import (BULK_QUANTITY, DAILY, DESSERT, DRINK, MEAL, SPORT, TECH, asked, channel_of, describe, fold,
                         from_model, has)

CONFIRMED = 10  # category 10 still waits for review
MEAL_BILL = {MEAL, DRINK, DESSERT}  # what a meal bill may include when estimating cost per person
NOT_SHOP_MEALS = {"超商", "量販", "超市"}
STORES = {"超商", "量販"}
# A share over a model's answers needs this many known ones once some are unknown, so a lucky few answers cannot
# stand for the whole (like meal_cost needing 3 costs and convenience_share 2 store bills).
MIN_KNOWN = 5
# Counts of yeses, and the model's question each one counts.
COUNTED = {"kitchen_per_month": "kitchen", "sport_supplies": "sport_supply", "sport_gear": "sport_gear",
           "car_care": "car_care", "home_items": "home", "stationery_items": "stationery", "alcohol_items": "alcohol",
           "pet_food_cat": "pet_food", "pet_food_dog": "pet_food", "pet_supply_cat": "pet_supply",
           "pet_supply_dog": "pet_supply"}
# A pet-shop bill with no known species and an item still waiting for the model: no evidence for either species, unlike
# judged items that name none (None), which split the visit as the rules always have.
WAITING = object()
SPLIT = {WAITING: (), "cat": (("cat", 1.0),), "dog": (("dog", 1.0),), None: (("cat", 0.5), ("dog", 0.5))}


def calendar_days(period, calendar):
    """All dates in the covered months, the days off among them, and the days inside long weekends.

    Days off are weekends and listed holidays, minus listed make-up workdays; a long weekend is three
    or more days off in a row.
    """
    holidays = {date.fromisoformat(day) for day in calendar["holidays"]}
    workdays = {date.fromisoformat(day) for day in calendar["workdays"]}
    days = []
    for year, month in period:
        day = date(year, month, 1)
        while day.month == month:
            days.append(day)
            day += timedelta(days=1)
    off = {day for day in days if day in holidays or (day.weekday() >= 5 and day not in workdays)}
    long_weekend, run = set(), []
    for day in days:
        if day in off and run and day - run[-1] == timedelta(days=1):
            run.append(day)
            continue
        if len(run) >= 3:
            long_weekend.update(run)
        run = [day] if day in off else []
    if len(run) >= 3:
        long_weekend.update(run)
    return days, off, long_weekend


def share(part, whole):
    return part / whole if whole else None


def count(pool, test):
    return sum(1 for entry in pool if test(entry))


def known(pool, flag):
    """The items whose answer to this question is known; an unknown answer is not a 'no', so a share leaves it out."""
    return [item for item in pool if item[flag] is not None]


def known_share(part, answered, total):
    """A share over the entries with a known answer; None when unknown answers leave fewer than MIN_KNOWN to rest on.

    With every answer known, as the keyword rules always give, this is plain share(): a small denominator is left to
    the trait's own minimum.
    """
    if answered < total and answered < MIN_KNOWN:
        return None
    return share(part, answered)


def estimated_share(decided, open_items, question, total):
    """A share of `total` items: the `decided` yeses a rule settles without the model, plus the `open_items` the model
    answers, estimated from those with a known answer; None when unknown answers leave fewer than MIN_KNOWN of them.

    Only the open items can be unknown, so the known answers among all the items are no fair sample (the rules' yeses or
    noes are always known); among the open items alone they are. With every answer known this is share(decided + yeses,
    total) exactly.
    """
    answered = known(open_items, question)
    if len(answered) < len(open_items) and len(answered) < MIN_KNOWN:
        return None
    if not answered:
        return share(decided, total)
    yeses = count(answered, lambda item: item[question])
    # (decided + len(open_items) * yeses / len(answered)) / total, in whole numbers until the one division.
    return share(decided * len(answered) + len(open_items) * yeses, total * len(answered))


def ranked(counter):
    """Most frequent first; ties fall back to the key so results never depend on input order."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def home_districts(located):
    """Districts holding at least a fifth of the located bills (two at most), most bills first: where someone lives and works."""
    districts = Counter(invoice["district"] for invoice in located)
    total = sum(districts.values())
    return [district for district, seen in ranked(districts)[:2] if seen >= total * 0.2]


def home_cities(located):
    """Cities of the home districts."""
    return {district[:3] for district in home_districts(located)}


def gather(rows, context, attributes=None):
    """Answer the item questions once per line, then group the lines into invoices.

    The answers come from the keyword rules, or from `attributes` when given: {name: a model's fields, or None while
    the name waits for the model}. Each line says whether its name is still waiting.
    """
    brands, vocabulary = context["brands"], context["vocabulary"]
    channels, lines, invoices = {}, [], {}
    for row in rows:
        merchant = row["merchant"]
        if merchant not in channels:
            channels[merchant] = channel_of(merchant, brands, vocabulary)
        fields = None if attributes is None else attributes.get(row["name"])
        answers = (describe(row, channels[merchant], vocabulary) if attributes is None
                   else from_model(row, channels[merchant], fields, vocabulary))
        line = {**row, "channel": channels[merchant], **answers, "waiting": attributes is not None and fields is None}
        lines.append(line)
        invoice = invoices.setdefault(row["invoice"], {
            "date": row["date"], "merchant": merchant, "channel": channels[merchant],
            # Online, delivery and utility sellers print a company address, not where the buyer was.
            "district": None if has(merchant, vocabulary["remote_sellers"]) else row.get("district"),
            "total": 0, "food": 0, "portions": 0, "lines": []})
        invoice["total"] += row["amount"]
        if not row["provisional"] and row["category"] in MEAL_BILL:
            invoice["food"] += row["amount"]
            # Main-dish portions stand in for the number of people a bill fed.
            if row["category"] == MEAL and row["amount"] > 0:
                invoice["portions"] += row["quantity"]
        invoice["lines"].append(line)
    return lines, invoices


def valid_items(lines):
    """Paid, confirmed lines; one portion per item and invoice."""
    seen, items = set(), []
    for line in lines:
        key = (line["invoice"], line["name"])
        if line["amount"] > 0 and not line["provisional"] and line["category"] < CONFIRMED and key not in seen:
            seen.add(key)
            items.append(line)
    return items


def category_counts(rows):
    """Valid items per confirmed category, for the category comparison on the connection page."""
    counts = [0] * CONFIRMED
    for item in valid_items(rows):
        counts[item["category"]] += 1
    return counts


def average(values):
    return mean(values) if values else None


def in_month(entries, year, month):
    return [entry for entry in entries if (entry["date"].year, entry["date"].month) == (year, month)]


def routine(items, paid, period):
    """Per month: how often names repeat, how concentrated the shops are, and how many shops were one-offs."""
    repeat, focus, one_off = [], [], []
    for year, month in period:
        bought, bills = in_month(items, year, month), in_month(paid, year, month)
        if bought:
            repeat.append(1 - len({fold(item["name"]) for item in bought}) / len(bought))
        if bills:
            shops = Counter(invoice["merchant"] for invoice in bills)
            focus.append(sum(seen for _, seen in shops.most_common(3)) / len(bills))
            one_off.append(count(shops.values(), lambda seen: seen == 1) / len(shops))
    return average(repeat), average(focus), average(one_off)


def quick_habit_meals(meals, off):
    """Workday quick meals whose name was bought on at least three different workdays."""
    workday_meals = [item for item in meals if item["date"] not in off]
    dates = {}
    for item in workday_meals:
        if item["quick"]:
            dates.setdefault(fold(item["name"]), set()).add(item["date"])
    habits = {name for name, seen in dates.items() if len(seen) >= 3}
    return [item for item in workday_meals if item["quick"] and fold(item["name"]) in habits]


def weekday_quick_share(meals, off):
    """Workdays with a quick meal that was bought on at least three different workdays, over workdays with a meal
    whose quick answer is known."""
    workday_meals = [item for item in meals if item["date"] not in off]
    answered = {item["date"] for item in known(workday_meals, "quick")}
    workdays = {item["date"] for item in workday_meals}
    return known_share(len({item["date"] for item in quick_habit_meals(meals, off)}), len(answered), len(workdays))


def bill_species(invoice):
    """The one species a pet-shop bill's pet items name, or None when they name neither or both; WAITING when they name
    none and an item on the bill still waits for the model."""
    named = {line["species"] for line in invoice["lines"] if line["species"] and (line["pet_food"] or line["pet_supply"])}
    if not named and any(line["waiting"] for line in invoice["lines"]):
        return WAITING
    return named.pop() if len(named) == 1 else None


def pet_signals(items, paid, months):
    pets = {"cat": Counter(), "dog": Counter()}
    for item in items:
        for kind in ("pet_food", "pet_supply"):
            if item[kind]:
                for species, part in SPLIT[item["species"]]:
                    pets[species][kind] += part
    shop_bills = [bill_species(invoice) for invoice in paid if invoice["channel"] == "寵物"]
    for named in shop_bills:
        for species, part in SPLIT[named]:
            pets[species]["visits"] += part
    signals = {f"pet_{kind}_{species}": pets[species][key] / months
               for species in ("cat", "dog") for kind, key in (("food", "pet_food"), ("supply", "pet_supply"), ("visits", "visits"))}
    if shop_bills and all(named is WAITING for named in shop_bills):
        # Pet-shop visits, but every one of them still waits for the model: they say nothing about either species.
        signals["pet_visits_cat"] = signals["pet_visits_dog"] = None
    return signals


def measure(rows, period, context, attributes=None):
    """Raw signals (None when they cannot be measured), the counts traits require, calendar constants, and the
    purchases each signal counted.

    With a model's answers (see gather for `attributes`) an unknown answer is never a no: a share leaves out the items
    whose answer is unknown and needs MIN_KNOWN known ones once some are unknown (fresh_share and bulk_share estimate
    only the part no rule decides, see estimated_share), and a count of yeses with not one known answer among the items
    it asks about is None.
    """
    days, off, long_weekend = calendar_days(period, context["calendar"])
    months = len(period)
    lines, invoices = gather(rows, context, attributes)
    items = valid_items(lines)
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    paid_bills = {key for key, invoice in invoices.items() if invoice["total"] > 0}
    food = [item for item in items if item["food"]]
    meals = [item for item in items if item["category"] == MEAL]
    drinks = [item for item in items if item["category"] == DRINK]
    daily = [item for item in items if item["category"] == DAILY]
    # Food that is not fresh is never for cooking and three of a kind are always bulk: only these need an answer.
    fresh = [item for item in food if asked("cooking", item["category"])]
    singles = [item for item in daily if item["quantity"] < BULK_QUANTITY]
    tech = [item for item in items if item["category"] == TECH]
    store_food = [item for item in food if item["channel"] == "超商"]
    portioned = {key: invoice for key, invoice in invoices.items() if invoice["portions"] and invoice["food"] > 0}
    costs = [invoice["food"] / invoice["portions"] for invoice in portioned.values()]
    located = [invoice for invoice in paid if invoice["district"]]
    home = home_cities(located)
    away = [invoice for invoice in located if invoice["district"][:3] not in home] if home else []
    trips = {invoice["date"] for invoice in away} | {invoice["date"] for invoice in paid if invoice["channel"] == "住宿"}
    daily_spend = Counter()
    for item in daily:
        daily_spend[item["invoice"]] += item["amount"]
    store_bills = [invoices[key] for key in daily_spend if invoices[key]["channel"] in STORES]
    off_bills = {key: invoice for key, invoice in invoices.items() if key in paid_bills and invoice["date"] in off}
    pet_bills = {key: bill_species(invoice) for key, invoice in invoices.items() if key in paid_bills and invoice["channel"] == "寵物"}
    monthly = Counter((item["date"].year, item["date"].month, fold(item["name"])) for item in items)
    spent = sum(invoice["total"] for invoice in paid)
    repeat_rate, shop_focus, new_shop_share = routine(items, paid, period)
    other = {"cat": "dog", "dog": "cat"}

    def visits(channel):
        return count(paid, lambda invoice: invoice["channel"] == channel) / months

    def flagged(flag):
        return [item for item in items if item[flag]]

    def at(channel):
        # Only paid bills count as visits, so only their purchases are listed.
        return [item for item in items if item["channel"] == channel and item["invoice"] in paid_bills]

    # The purchases each signal counts, so the page can name them. Most signals below are worked out from these
    # very lists, so each rule is written once. Signals about where someone shopped or travelled list nothing.
    behind = {
        "meal_cost": [item for item in meals if item["invoice"] in portioned],
        "clearance_share": [item for item in food if item["clearance"]],
        "premium_drink_share": [item for item in drinks if item["amount"] / max(item["quantity"], 1) >= 100],
        "store_meal_share": [item for item in meals if item["channel"] == "超商"],
        "weekday_quick_share": quick_habit_meals(meals, off),
        "store_clearance_share": [item for item in store_food if item["clearance"]],
        "shop_meal_share": [item for item in meals if item["channel"] not in NOT_SHOP_MEALS],
        "fresh_share": [item for item in food if item["cooking"]],
        "ready_meal_share": meals,
        "kitchen_per_month": flagged("kitchen"),
        "sugar_mean": [item for item in drinks if item["sugar"] is not None],
        "dessert_share": [item for item in food if item["category"] == DESSERT],
        "repeat_rate": [item for item in items if monthly[(item["date"].year, item["date"].month, fold(item["name"]))] > 1],
        "shop_focus": [], "new_shop_share": [],
        "sport_visits": [item for item in items if item["category"] == SPORT],
        "sport_supplies": flagged("sport_supply"), "sport_gear": flagged("sport_gear"),
        "fuel_visits": at("加油"), "parking_visits": at("停車"), "car_care": flagged("car_care"),
        "away_share": [], "stays": at("住宿"), "long_trips": at("長途交通"),
        "convenience_share": [item for item in daily if invoices[item["invoice"]]["channel"] == "超商"],
        "bulk_share": [item for item in daily if item["bulk"]],
        "small_daily_visits": [item for item in daily if daily_spend[item["invoice"]] < 150],
        "home_items": flagged("home"), "stationery_items": flagged("stationery"), "select_visits": at("選物"),
        "tech_items": tech, "tech_spend": tech, "tech_visits": at("3C"),
        "offday_invoice_share": [item for item in items if item["invoice"] in off_bills],
        "offday_amount_share": [item for item in items if item["invoice"] in off_bills],
        "holiday_trip_share": [],
        "fun_visits": flagged("fun"), "fun_kinds": flagged("fun"),
        **{f"pet_{kind}_{species}": [item for item in items if item[f"pet_{kind}"] and item["species"] != other[species]]
           for species in ("cat", "dog") for kind in ("food", "supply")},
        **{f"pet_visits_{species}": [item for item in items if item["invoice"] in pet_bills
                                     and pet_bills[item["invoice"]] is not WAITING
                                     and pet_bills[item["invoice"]] != other[species]] for species in ("cat", "dog")},
        "alcohol_items": flagged("alcohol"), "bar_visits": at("酒吧"),
    }

    def bills(key):
        return {item["invoice"] for item in behind[key]}

    signals = {
        "meal_cost": median(costs) if len(costs) >= 3 else None,
        "clearance_share": known_share(len(behind["clearance_share"]), len(known(food, "clearance")), len(food)),
        "premium_drink_share": share(len(behind["premium_drink_share"]), len(drinks)),
        "store_meal_share": share(len(behind["store_meal_share"]), len(meals)),
        "weekday_quick_share": weekday_quick_share(meals, off),
        "store_clearance_share": known_share(len(behind["store_clearance_share"]), len(known(store_food, "clearance")),
                                             len(store_food)),
        "shop_meal_share": share(len(behind["shop_meal_share"]), len(meals)),
        "fresh_share": estimated_share(0, fresh, "cooking", len(food)),
        "ready_meal_share": share(len(meals), len(food)),
        "kitchen_per_month": len(behind["kitchen_per_month"]) / months,
        "sugar_mean": mean(item["sugar"] for item in behind["sugar_mean"]) if behind["sugar_mean"] else None,
        "dessert_share": share(len(behind["dessert_share"]), len(food)),
        "repeat_rate": repeat_rate, "shop_focus": shop_focus, "new_shop_share": new_shop_share,
        "sport_visits": len(bills("sport_visits")) / months,
        "sport_supplies": len(behind["sport_supplies"]) / months,
        "sport_gear": len(behind["sport_gear"]) / months,
        "fuel_visits": visits("加油"), "parking_visits": visits("停車"),
        "car_care": len(behind["car_care"]) / months,
        "away_share": share(len(away), len(located)) if home else None,
        "stays": visits("住宿"), "long_trips": visits("長途交通"),
        "convenience_share": share(len(bills("convenience_share")), len(store_bills)) if len(store_bills) >= 2 else None,
        "bulk_share": estimated_share(len(daily) - len(singles), singles, "bulk", len(daily)),
        "small_daily_visits": len(bills("small_daily_visits")) / months,
        "home_items": len(behind["home_items"]) / months,
        "stationery_items": len(behind["stationery_items"]) / months,
        "select_visits": visits("選物"),
        "tech_items": len(tech) / months,
        "tech_spend": sum(min(item["amount"], 3000) for item in tech) / months,
        "tech_visits": visits("3C"),
        "offday_invoice_share": share(len(off_bills), len(paid)),
        "offday_amount_share": share(sum(invoice["total"] for invoice in off_bills.values()), spent),
        "holiday_trip_share": share(len(trips & long_weekend), len(trips)),
        "fun_visits": len(bills("fun_visits")) / months,
        "fun_kinds": len({item["fun"] for item in behind["fun_kinds"]}),
        **pet_signals(items, paid, months),
        "alcohol_items": len(behind["alcohol_items"]) / months,
        "bar_visits": visits("酒吧"),
    }
    # The rules answer every one of these questions, so only a model's unknowns leave a signal unmeasured here.
    for signal, question in COUNTED.items():
        pool = [item for item in items if asked(question, item["category"])]
        if pool and not known(pool, question):
            signals[signal] = None
    # Once the model has judged a name, no kind of fun means not fun; with every name still waiting and no shop saying
    # fun, nothing is known about fun at all.
    if items and all(item["waiting"] for item in items) and not behind["fun_visits"]:
        signals["fun_visits"] = signals["fun_kinds"] = None
    # A signal that cannot be measured lists nothing; a signal missing from `behind` fails here instead of listing nothing.
    if behind.keys() != signals.keys():
        raise KeyError(sorted(behind.keys() ^ signals.keys()))
    purchases = {key: behind[key] if value is not None else [] for key, value in signals.items()}
    counts = {
        "items": len(items), "food_items": len(food), "meal_items": len(meals), "store_food_items": len(store_food),
        "known_sugar_drinks": len(behind["sugar_mean"]),
        "district_invoices": len(located), "daily_items": len(daily), "invoices": len(paid),
        "trip_days": len(trips), "long_holidays": 1 if long_weekend else 0,
    }
    offday_share = len(off) / len(days)
    constants = {"offday_share": offday_share, "offday_double": min(1.0, 2 * offday_share),
                 "long_holiday_share": len(long_weekend) / len(days)}
    return {"signals": signals, "counts": counts, "constants": constants, "purchases": purchases}
