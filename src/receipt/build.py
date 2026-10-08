"""Generate a standalone HTML report from configuration, source assets and local data."""
import argparse
from html import escape
import json
import re
from pathlib import Path

from .invoices import build_month
from .demo import build_demo
from .personas import PERIOD, build_friends, build_personas
from .places import areas_of, distance, load_regions
from .signals import category_counts
from .similarity import compare, percent
from .traits import build_vector, dated, load_context, population_vectors, relative, similarity_model

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
    # A product name must not be able to introduce an HTML script element.
    payload = json.dumps(value, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    return f"'use strict';\nconst {name} = " + payload + ";\n"


def trait_words(settings):
    """How the match page names each trait: its two ends, or the short word for a habit."""
    words = []
    for trait in settings["traits"]:
        entry = {"id": trait["id"], "name": trait["name"], "kind": trait["kind"]}
        entry.update({"ends": trait["ends"]} if trait["kind"] == "two_sided" else {"habit": trait["habit"]})
        words.append(entry)
    return words


def build_matches(months, population, context, regions, is_demo):
    """Everyone's taste vector, measured from the average person, for the match page to score in the browser."""
    settings = context["traits"]
    vectors = population_vectors(population, list(PERIOD), context)
    rows, period = dated(months)
    mine = areas_of(rows, context)
    people = []
    for person in population:
        areas = areas_of(person["rows"], context)
        people.append({"name": person["name"], "vector": vectors["relative"][person["name"]],
                       "distance": distance(mine, areas, regions), "place": areas[0] if areas else None,
                       "counts": category_counts(person["rows"])})
    return {
        "isDemo": is_demo, "population": len(people),
        "personaMonths": [f"{year}-{month:02}" for year, month in PERIOD],
        "model": similarity_model(settings), "traits": trait_words(settings),
        "settings": {**settings["match"], "min_items": settings["min_items"]},
        "me": {"vector": relative(build_vector(rows, period, context), vectors["centers"]), "months": sorted(months),
               "areas": mine, "counts": category_counts(rows)},
        "people": people,
    }


def taste_summary(months, population, friends, context):
    """My taste vector and my similarity to each fictional person, all measured from the average person."""
    vectors = population_vectors(population, list(PERIOD), context, extra=friends)
    rows, period = dated(months)
    me = relative(build_vector(rows, period, context), vectors["centers"])
    model = similarity_model(context["traits"])
    scores = [compare(me, vectors["relative"][person["name"]], model)["score"] for person in population]
    return me, sorted(score for score in scores if score is not None)


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
    comparison = (WEB / "taste-comparison.html").read_text(encoding="utf-8")
    comparison = embed_scripts(comparison, {"taste-profile.js": scripts["taste-profile.js"]})
    html = embed_page(html, "taste-page-source", comparison)
    context = load_context(ROOT)
    population = build_personas(context["calendar"])
    matches = build_matches(months, population, context, load_regions(ROOT), not args.private)
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
    me, scores = taste_summary(months, population, build_friends(context["calendar"]), context)
    if me is None or not scores:
        print("taste vector: not enough data to compare")
    else:
        middle = scores[len(scores) // 2]
        print(f"taste similarity to {len(scores)} fictional people: highest {percent(scores[-1])}%, "
              f"median {percent(middle)}%, lowest {percent(scores[0])}%")


if __name__ == "__main__":
    main()
