"""ASSISTANT-DRAFTED partial reference. Never substitutes for the user's human review."""
import json
from pathlib import Path
from lab_core import ATTRIBUTES, BASIC

ROOT = Path(__file__).resolve().parent


def check_fixture(data):
    if data['source_sha256'] != '1ea2b762713ae4562da70f0f155fa0fe2c4b3f045f526ef4da7930663f32556a':
        raise ValueError('Draft is pinned to the inspected March CSV; label another source separately.')


def main():
    data = json.loads((ROOT / 'private/prepared.json').read_text(encoding='utf-8'))
    check_fixture(data)
    # IDs below are reviewed against this copied March fixture, not inferred by the tested models.
    by_id = {x['id']: x for x in data['items']}
    if len(by_id) != 28:
        raise ValueError('Draft labels only apply to the inspected March fixture; review a new source manually.')
    meals = {'i0002','i0003','i0004','i0005','i0006','i0007','i0008','i0009','i0010','i0013','i0022','i0024','i0025','i0026'}
    snacks = {'i0012','i0017','i0019'}
    alcoholic = {'i0018','i0020','i0021'}
    drinks = alcoholic | {'i0014','i0028'}
    entries = []
    for item in data['items']:
        key = item['id']
        attrs = {name: False for name in ATTRIBUTES}
        attrs.update(sugar=None, fun=None, species=None)
        basic = {name: False for name in BASIC}
        if key in meals:
            basic.update(food=True, meal=True)
        if key in snacks:
            basic['food'] = True
        if key in drinks:
            basic.update(food=True, drink=True)
        if key in alcoholic:
            attrs['alcohol'] = True
        if key == 'i0001':
            basic['sport'] = True
        if key == 'i0014':
            attrs['sugar'] = 0
        if key == 'i0027':
            attrs['cooking'] = True
            basic.update(food=True, fresh=True)
        if item['quantity'] >= 3:
            attrs['bulk'] = True
        notes = ''
        if key == 'i0015':
            # Surcharge naming does not tell us what actual food was purchased.
            basic = dict.fromkeys(BASIC)
            notes = '加價項目無法確定實際商品，basic 保留未知；使用者需核對。'
        if key == 'i0016':
            # A collectible stamp may be a reward rather than purchased stationery.
            attrs['stationery'] = None
            basic['daily'] = None
            notes = '印花貼紙可能是集點而非文具；使用者需確認，不能當可靠正例。'
        if key == 'i0014':
            notes = '依 0分糖 暫判無糖飲品；黑米本體仍需使用者確認。'
        entries.append({'id': key, 'name': item['name'], 'attributes': attrs, 'basic': basic, 'notes': notes})
    draft = {'status': 'ASSISTANT_DRAFT_NOT_USER_VERIFIED', 'source_sha256': data['source_sha256'],
             'warning': 'Diagnostic agreement only, not real-world model accuracy. Null means expected unknown/not applicable in this draft.',
             'items': entries}
    (ROOT / 'private/draft-reference.json').write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved 28 assistant-draft labels. User verification remains required.')


if __name__ == '__main__':
    main()
