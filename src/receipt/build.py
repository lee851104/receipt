"""Generate a standalone HTML report from configuration, source assets and local data."""
import argparse
from html import escape
import json
import re
from pathlib import Path

from .invoices import build_month
from .demo import build_demo

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
    # A product name must not be able to introduce an HTML script element.
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    data_script = "'use strict';\nconst expenseReportData = " + payload + ";\n"
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
    marker = '<template id="taste-page-source"></template>'
    if html.count(marker) != 1:
        raise ValueError("Expected exactly one embedded comparison template")
    html = html.replace(marker, '<template id="taste-page-source">' + escape(comparison) + '</template>', 1)
    processed = ROOT / "data" / ("private" if args.private else "processed")
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "report-data.js").write_text(data_script, encoding="utf-8")
    output = "invoice-insights-private.html" if args.private else "invoice-insights.html"
    (ROOT / output).write_text(html, encoding="utf-8")
    for key, month in months.items():
        print(key, len(month["rows"]), "rows; total", sum(row["amount"] for row in month["rows"]))


if __name__ == "__main__":
    main()
