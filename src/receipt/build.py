"""Generate a standalone HTML report from configuration, source assets and local data."""
import argparse
from html import escape
import json
import re
from pathlib import Path

from .invoices import build_month
from .demo import build_demo
from .personas import PERIOD, build_friends, build_personas
from .places import areas_of, closest_area, distance, load_regions
from .signals import category_counts
from .similarity import compare, percent
from .traits import dated, explain, load_context, population, signal_ids, similarity_model

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "web"
CONFIG = ROOT / "configs" / "report.json"


def embed_scripts(html, scripts):
    """Refresh inline scripts, accepting either original references or a prior build."""
    for name, source in scripts.items():
        pattern = (r'<script\b[^>]*\b(?:src|data-source)="'
                   + re.escape(name) + r'"[^>]*>.*?</script\s*>')
        # An HTML parser recognizes closing script tags even inside JS strings.
        safe_source = re.sub(r'</script', lambda match: r'<\/' + match[0][2:],
                             source, flags=re.IGNORECASE)
        replacement = f'<script data-source="{name}">\n{safe_source.rstrip()}\n</script>'
        html, count = re.subn(pattern, lambda _: replacement, html, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f'Expected exactly one script block for {name}; got {count}')
    return html


def embed_page(html, template_id, page):
    """Place a standalone page inside a template element so the report stays one file."""
    marker = f'<template id="{template_id}"></template>'
    if html.count(marker) != 1:
        raise ValueError(f"Expected exactly one template: {template_id}")
    return html.replace(marker, f'<template id="{template_id}">' + escape(page) + "</template>", 1)


def script_constant(name, value):
    # Compact JSON keeps the single-file report small; a product name must not be able to introduce a script element.
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f"'use strict';\nconst {name} = " + payload + ";\n"


def trait_words(settings):
    """How the match page names each trait: its two ends, or the short word for a habit, and its group if any."""
    words = []
    for trait in settings["traits"]:
        entry = {"id": trait["id"], "name": trait["name"], "kind": trait["kind"]}
        entry.update({"ends": trait["ends"]} if trait["kind"] == "two_sided" else {"habit": trait["habit"]})
        if "group" in trait:
            entry["group"] = trait["group"]
        words.append(entry)
    return words


def vector_of(explained):
    """The taste vector of an explain() result, or None when the person had too little data."""
    return None if explained is None else explained["vector"]


def rounded(value):
    """Four decimals, through lists and dicts: pushes and signals only draw lines and fill sentences."""
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    # Adding 0.0 turns -0.0 into 0.0, so a push of nothing never prints as negative.
    return round(value, 4) + 0.0 if isinstance(value, float) else value


def drawing_of(explained, order):
    """What the network graph draws for one person: each signal's push on each trait, and the measured signals
    listed in signal_ids() order so their names are not repeated for everyone."""
    if explained is None:
        return {"pushes": None, "signals": None}
    return {"pushes": rounded(explained["pushes"]), "signals": [rounded(explained["signals"][key]) for key in order]}


def build_matches(rows, months, people, tastes, me, context, regions, is_demo):
    """Everyone's taste vector for the match page to score in the browser."""
    settings = context["traits"]
    order = signal_ids(settings)
    mine = areas_of(rows, context)
    entries = []
    for person in people:
        areas = areas_of(person["rows"], context)
        entries.append({"name": person["name"], "vector": vector_of(tastes[person["name"]]),
                        **drawing_of(tastes[person["name"]], order),
                        "distance": distance(mine, areas, regions), "place": closest_area(mine, areas, regions),
                        "counts": category_counts(person["rows"])})
    return {
        "isDemo": is_demo, "population": len(entries),
        "personaMonths": [f"{year}-{month:02}" for year, month in PERIOD],
        "model": similarity_model(settings), "traits": trait_words(settings),
        "settings": {**settings["match"], "min_items": settings["min_items"]},
        "me": {"vector": vector_of(me), **drawing_of(me, order), "months": sorted(months), "areas": mine,
               "counts": category_counts(rows)},
        "people": entries,
    }


def trait_network_data(settings, tastes, friends):
    """What the connection page needs to draw the network graph by itself: the model, every trait with its
    words, lines and signal ids, every signal's label and unit, the readout fallbacks, and the three demo friends."""
    order = signal_ids(settings)
    labels = {}
    traits = trait_words(settings)
    for entry, trait in zip(traits, settings["traits"]):
        if "short" in trait:
            entry["short"] = trait["short"]
        entry["lines"] = trait["lines"]
        entry["signals"] = [signal["id"] for signal in trait["signals"]]
        for signal in trait["signals"]:
            labels.setdefault(signal["id"], {"id": signal["id"], "label": signal["label"], "unit": signal["unit"]})
    return {
        "model": similarity_model(settings), "traits": traits, "signals": [labels[key] for key in order],
        "readout": settings["readout"],
        "friends": {friend["name"]: {"vector": vector_of(tastes[friend["name"]]), **drawing_of(tastes[friend["name"]], order)}
                    for friend in friends},
    }


def taste_summary(me, people, tastes, context):
    """My similarity to each fictional person, lowest first; empty when I have too little data."""
    if me is None:
        return []
    model = similarity_model(context["traits"])
    scores = [compare(me["vector"], vector_of(tastes[person["name"]]), model)["score"] for person in people]
    return sorted(score for score in scores if score is not None)


def main():
    parser = argparse.ArgumentParser(description="Build a public demo, or an explicitly requested private report.")
    parser.add_argument("--private", action="store_true", help="Read data/private/report.json and write invoice-insights-private.html")
    args = parser.parse_args()
    config_path = ROOT / "data" / "private" / "report.json" if args.private else CONFIG
    config = json.loads(config_path.read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / config["category_catalog"]).read_text(encoding="utf-8"))
    if args.private:
        months = {}
        for filename in config["input_files"]:
            key, month = build_month(ROOT / filename, catalog)
            if key in months:
                raise ValueError(f"Duplicate month in input files: {key}")
            months[key] = month
    else:
        months = build_demo(catalog)
    data = {"isDemo": not args.private, "categories": config["categories"], "months": months}
    data_script = script_constant("expenseReportData", data)
    scripts = {"report-data.js": data_script}
    for name in ("insights-ui.js", "monthly-comparison.js", "comparison-ui.js", "flow-navigation.js", "taste-profile.js", "taste-export.js", "taste-navigation.js"):
        scripts[name] = (WEB / name).read_text(encoding="utf-8")
    template = (WEB / "invoice-insights.html").read_text(encoding="utf-8")
    style_link = '<link rel="stylesheet" href="styles.css">'
    if template.count(style_link) != 1:
        raise ValueError("Expected exactly one stylesheet link in the HTML template")
    stylesheet = (WEB / "styles.css").read_text(encoding="utf-8")
    html = embed_scripts(template.replace(style_link, "<style>" + stylesheet + "</style>", 1), scripts)
    context = load_context(ROOT)
    people = build_personas(context["calendar"])
    friends = build_friends(context["calendar"])
    # Everyone's taste is worked out once, here, and shared by both pages and the summary below.
    tastes = population([*people, *friends], list(PERIOD), context)
    comparison = embed_scripts((WEB / "taste-comparison.html").read_text(encoding="utf-8"), {
        "taste-profile.js": scripts["taste-profile.js"],
        "trait-network-data.js": script_constant("traitNetworkData", trait_network_data(context["traits"], tastes, friends))})
    html = embed_page(html, "taste-page-source", comparison)
    rows, period = dated(months)
    me = explain(rows, period, context)
    matches = build_matches(rows, months, people, tastes, me, context, load_regions(ROOT), not args.private)
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
        "trait-similarity.js": (WEB / "trait-similarity.js").read_text(encoding="utf-8"),
        "match-filter.js": (WEB / "match-filter.js").read_text(encoding="utf-8"),
        "match-data.js": script_constant("matchReportData", matches)})
    html = embed_page(html, "match-page-source", match_page)
    processed = ROOT / "data" / ("private" if args.private else "processed")
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "report-data.js").write_text(data_script, encoding="utf-8")
    output = "invoice-insights-private.html" if args.private else "invoice-insights.html"
    (ROOT / output).write_text(html, encoding="utf-8")
    for key, month in months.items():
        print(key, len(month["rows"]), "rows; total", sum(row["amount"] for row in month["rows"]))
    scores = taste_summary(me, people, tastes, context)
    if not scores:
        print("taste vector: not enough data to compare")
    else:
        middle = scores[len(scores) // 2]
        print(f"taste similarity to {len(scores)} fictional people: highest {percent(scores[-1])}%, "
              f"median {percent(middle)}%, lowest {percent(scores[0])}%")


if __name__ == "__main__":
    main()
