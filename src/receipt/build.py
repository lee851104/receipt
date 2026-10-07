"""Generate a standalone HTML report from configuration, source assets and local data."""
import argparse
from html import escape
import json
import re
from pathlib import Path

from .invoices import build_month
from .demo import build_demo
from .matching import eligible, ready
from .personas import MONTHS, build_personas
from .tags import build_profile

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


def build_matches(months, categories, is_demo):
    """Profile the report and keep only the scores and words the match page shows."""
    settings = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
    brands = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
    me = build_profile([row for month in months.values() for row in month["rows"]], categories, brands, settings)
    people = [{"name": person["name"], "profile": build_profile(person["rows"], categories, brands, settings)}
              for person in build_personas()]
    return {
        "isDemo": is_demo, "population": len(people),
        "personaMonths": [f"{year}-{month:02}" for year, month, _ in MONTHS],
        "settings": {key: settings[key] for key in ("weights", "thresholds", "price_levels", "top_matches", "category_min_items")},
        "me": {"ready": ready(me), "item_count": me["item_count"], "months": sorted(months), "areas": me["areas"],
               "tags": [{"dimension": tag["dimension"], "text": tag["text"]} for tag in me["tags"]],
               "counts": me["category_counts"]},
        "candidates": eligible(me, people, settings) if ready(me) else [],
    }


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
    matches = build_matches(months, config["categories"], not args.private)
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
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
    print("match candidates:", len(matches["candidates"]), "of", matches["population"], "fictional people")


if __name__ == "__main__":
    main()
