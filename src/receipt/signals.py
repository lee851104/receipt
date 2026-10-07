"""Measure one person's purchases: the shares, monthly counts and medians the taste traits weigh."""
from collections import Counter
from datetime import date, timedelta
from statistics import mean, median

from .attributes import DAILY, DESSERT, DRINK, MEAL, SPORT, TECH, channel_of, describe, fold, has

CONFIRMED = 10  # category 10 still waits for review
MEAL_BILL = {MEAL, DRINK, DESSERT}  # what a meal bill may include when estimating cost per person
NOT_SHOP_MEALS = {"超商", "量販", "超市"}
STORES = {"超商", "量販"}
SPLIT = {"cat": (("cat", 1.0),), "dog": (("dog", 1.0),), None: (("cat", 0.5), ("dog", 0.5))}


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


def ranked(counter):
    """Most frequent first; ties fall back to the key so results never depend on input order."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def home_cities(located):
    """Cities of the districts holding at least a fifth of the located bills (two at most): where someone lives and works."""
    districts = Counter(invoice["district"] for invoice in located)
    total = sum(districts.values())
    return {district[:3] for district, seen in ranked(districts)[:2] if seen >= total * 0.2}


def gather(rows, context):
    """Answer the item questions once per line, then group the lines into invoices."""
    brands, vocabulary = context["brands"], context["vocabulary"]
    channels, lines, invoices = {}, [], {}
    for row in rows:
        merchant = row["merchant"]
        if merchant not in channels:
            channels[merchant] = channel_of(merchant, brands, vocabulary)
        line = {**row, "channel": channels[merchant], **describe(row, channels[merchant], vocabulary)}
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
    """Paid, confirmed lines; one portion per item and invoice, as in the match tags."""
    seen, items = set(), []
    for line in lines:
        key = (line["invoice"], line["name"])
        if line["amount"] > 0 and not line["provisional"] and line["category"] < CONFIRMED and key not in seen:
            seen.add(key)
            items.append(line)
    return items


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


def weekday_quick_share(meals, off):
    """Workdays with a quick meal that was bought on at least three different workdays, over workdays with a meal."""
    workday_meals = [item for item in meals if item["date"] not in off]
    dates = {}
    for item in workday_meals:
        if item["quick"]:
            dates.setdefault(fold(item["name"]), set()).add(item["date"])
    habits = {name for name, seen in dates.items() if len(seen) >= 3}
    quick = {item["date"] for item in workday_meals if item["quick"] and fold(item["name"]) in habits}
    return share(len(quick), len({item["date"] for item in workday_meals}))


def pet_signals(items, paid, months):
    pets = {"cat": Counter(), "dog": Counter()}
    for item in items:
        for kind in ("pet_food", "pet_supply"):
            if item[kind]:
                for species, part in SPLIT[item["species"]]:
                    pets[species][kind] += part
    for invoice in paid:
        if invoice["channel"] == "寵物":
            known = {line["species"] for line in invoice["lines"] if line["species"]}
            for species, part in SPLIT[known.pop() if len(known) == 1 else None]:
                pets[species]["visits"] += part
    return {f"pet_{kind}_{species}": pets[species][key] / months
            for species in ("cat", "dog") for kind, key in (("food", "pet_food"), ("supply", "pet_supply"), ("visits", "visits"))}


def measure(rows, period, context):
    """Raw signals (None when they cannot be measured), the counts traits require, and calendar constants."""
    days, off, long_weekend = calendar_days(period, context["calendar"])
    months = len(period)
    lines, invoices = gather(rows, context)
    items = valid_items(lines)
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    food = [item for item in items if item["food"]]
    meals = [item for item in items if item["category"] == MEAL]
    drinks = [item for item in items if item["category"] == DRINK]
    daily = [item for item in items if item["category"] == DAILY]
    tech = [item for item in items if item["category"] == TECH]
    sugars = [item["sugar"] for item in drinks if item["sugar"] is not None]
    store_food = [item for item in food if item["channel"] == "超商"]
    costs = [invoice["food"] / invoice["portions"] for invoice in invoices.values()
             if invoice["portions"] and invoice["food"] > 0]
    located = [invoice for invoice in paid if invoice["district"]]
    home = home_cities(located)
    away = [invoice for invoice in located if invoice["district"][:3] not in home] if home else []
    trips = {invoice["date"] for invoice in away} | {invoice["date"] for invoice in paid if invoice["channel"] == "住宿"}
    daily_spend = Counter()
    for item in daily:
        daily_spend[item["invoice"]] += item["amount"]
    store_bills = [invoices[key] for key in daily_spend if invoices[key]["channel"] in STORES]
    fun = {}
    for item in items:
        if item["fun"]:
            fun.setdefault(item["invoice"], set()).add(item["fun"])
    spent = sum(invoice["total"] for invoice in paid)
    repeat_rate, shop_focus, new_shop_share = routine(items, paid, period)

    def visits(channel):
        return count(paid, lambda invoice: invoice["channel"] == channel) / months

    signals = {
        "meal_cost": median(costs) if len(costs) >= 3 else None,
        "clearance_share": share(count(food, lambda item: item["clearance"]), len(food)),
        "premium_drink_share": share(count(drinks, lambda item: item["amount"] / item["quantity"] >= 100), len(drinks)),
        "store_meal_share": share(count(meals, lambda item: item["channel"] == "超商"), len(meals)),
        "weekday_quick_share": weekday_quick_share(meals, off),
        "store_clearance_share": share(count(store_food, lambda item: item["clearance"]), len(store_food)),
        "shop_meal_share": share(count(meals, lambda item: item["channel"] not in NOT_SHOP_MEALS), len(meals)),
        "fresh_share": share(count(food, lambda item: item["cooking"]), len(food)),
        "ready_meal_share": share(len(meals), len(food)),
        "kitchen_per_month": count(items, lambda item: item["kitchen"]) / months,
        "sugar_mean": mean(sugars) if sugars else None,
        "dessert_share": share(count(food, lambda item: item["category"] == DESSERT), len(food)),
        "repeat_rate": repeat_rate, "shop_focus": shop_focus, "new_shop_share": new_shop_share,
        "sport_visits": len({item["invoice"] for item in items if item["category"] == SPORT}) / months,
        "sport_supplies": count(items, lambda item: item["sport_supply"]) / months,
        "sport_gear": count(items, lambda item: item["sport_gear"]) / months,
        "fuel_visits": visits("加油"), "parking_visits": visits("停車"),
        "car_care": count(items, lambda item: item["car_care"]) / months,
        "away_share": share(len(away), len(located)) if home else None,
        "stays": visits("住宿"), "long_trips": visits("長途交通"),
        "convenience_share": share(count(store_bills, lambda bill: bill["channel"] == "超商"), len(store_bills))
        if len(store_bills) >= 2 else None,
        "bulk_share": share(count(daily, lambda item: item["bulk"]), len(daily)),
        "small_daily_visits": count(daily_spend.values(), lambda amount: amount < 150) / months,
        "home_items": count(items, lambda item: item["home"]) / months,
        "stationery_items": count(items, lambda item: item["stationery"]) / months,
        "select_visits": visits("選物"),
        "tech_items": len(tech) / months,
        "tech_spend": sum(min(item["amount"], 3000) for item in tech) / months,
        "tech_visits": visits("3C"),
        "offday_invoice_share": share(count(paid, lambda invoice: invoice["date"] in off), len(paid)),
        "offday_amount_share": share(sum(invoice["total"] for invoice in paid if invoice["date"] in off), spent),
        "holiday_trip_share": share(len(trips & long_weekend), len(trips)),
        "fun_visits": len(fun) / months,
        "fun_kinds": len(set().union(*fun.values())),
        **pet_signals(items, paid, months),
        "alcohol_items": count(items, lambda item: item["alcohol"]) / months,
        "bar_visits": visits("酒吧"),
    }
    counts = {
        "items": len(items), "food_items": len(food), "meal_items": len(meals), "store_food_items": len(store_food),
        "known_sugar_drinks": len(sugars),
        "district_invoices": len(located), "daily_items": len(daily), "invoices": len(paid),
        "trip_days": len(trips), "long_holidays": 1 if long_weekend else 0,
    }
    offday_share = len(off) / len(days)
    constants = {"offday_share": offday_share, "offday_double": min(1.0, 2 * offday_share),
                 "long_holiday_share": len(long_weekend) / len(days)}
    return {"signals": signals, "counts": counts, "constants": constants}
