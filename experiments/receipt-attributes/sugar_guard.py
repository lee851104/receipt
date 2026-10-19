"""Reject unsupported sweetness guesses; this is not a nutrition estimator."""
from copy import deepcopy
import re
import unicodedata


def apply_sugar_guard(items, predictions):
    by_id = {item['id']: item for item in items}
    updated, overrides = deepcopy(predictions), []
    for prediction in updated:
        name = unicodedata.normalize('NFKC', by_id[prediction['id']]['name'])
        explicit = (any(word in name for word in ('無糖','无糖','零分糖','微糖','半糖','少糖','全糖','正常甜'))
                    or bool(re.search(r'\d+\s*分\s*糖', name)))
        value = prediction['attributes']['sugar']
        if value is not None and not explicit:
            overrides.append({'id':prediction['id'], 'field':'sugar', 'before':value, 'after':None,
                              'rule':'sweetness_requires_explicit_text_v1'})
            prediction['attributes']['sugar'] = None
    return {'predictions':updated, 'overrides':overrides}
