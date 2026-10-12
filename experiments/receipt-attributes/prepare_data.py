"""Prepare a PRIVATE local item list and an editable, initially empty human reference."""
import json
from pathlib import Path
from lab_core import prepare, ATTRIBUTES, BASIC

ROOT = Path(__file__).resolve().parent


def main():
    data = prepare(ROOT / 'private' / '0301-0331.csv')
    (ROOT / 'private' / 'prepared.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    review_path = ROOT / 'private' / 'human-review.json'
    if not review_path.exists():
        review = {'status': 'NOT_REVIEWED', 'source_sha256': data['source_sha256'], 'items': [
            {'id': x['id'], 'name': x['name'], 'merchant': x['merchant'], 'quantity': x['quantity'],
             'attributes': dict.fromkeys(ATTRIBUTES), 'basic': dict.fromkeys(BASIC), 'notes': ''}
            for x in data['items']]}
        review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Prepared {len(data['rows'])} rows -> {len(data['items'])} merchant/name/quantity groups; no cloud calls.")


if __name__ == '__main__':
    main()
