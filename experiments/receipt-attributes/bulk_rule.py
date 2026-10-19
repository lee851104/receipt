"""Positive-only bulk evidence from the existing specification; no answer lookup."""
from copy import deepcopy
import re


def apply_bulk_rule(items, predictions):
    by_id = {item['id']: item for item in items}
    updated, overrides = deepcopy(predictions), []
    for prediction in updated:
        item = by_id[prediction['id']]
        name = item['name']
        evidence = (item['quantity'] >= 3 or bool(re.search(r'\d+\s*入', name))
                    or any(word in name for word in ('整箱','箱裝','家庭號','量販包')))
        if evidence and prediction['attributes']['bulk'] is not True:
            overrides.append({'id':item['id'], 'field':'bulk', 'before':prediction['attributes']['bulk'],
                              'after':True, 'rule':'explicit_quantity_or_packaging_v1'})
            prediction['attributes']['bulk'] = True
    return {'predictions':updated, 'overrides':overrides}
