"""Where someone shops most, and how far apart two people's home districts are."""
import json

from .signals import gather, home_districts


def load_regions(root):
    """City or county → region, from configs/regions.json."""
    regions = json.loads((root / "configs" / "regions.json").read_text(encoding="utf-8"))
    return {city: region for region, cities in regions.items() for city in cities}


def areas_of(rows, context):
    """Someone's home districts: at least a fifth of their located, paid bills, two at most, most bills first."""
    _, invoices = gather(rows, context)
    return home_districts([invoice for invoice in invoices.values() if invoice["total"] > 0 and invoice["district"]])


def place_distance(a, b, regions):
    """0 for the same district, 1 for the same city or county, 2 for the same region, 3 otherwise."""
    if a == b:
        return 0
    if a[:3] == b[:3]:
        return 1
    region = regions.get(a[:3])
    return 2 if region is not None and region == regions.get(b[:3]) else 3


def distance(mine, theirs, regions):
    """The closest pair of home districts; 3 when either side has none."""
    return min((place_distance(a, b, regions) for a in mine for b in theirs), default=3)


def closest_area(mine, theirs, regions):
    """Their home district closest to mine, keeping their order on ties; their first one when I have none."""
    if not theirs:
        return None
    if not mine:
        return theirs[0]
    return min(theirs, key=lambda area: min(place_distance(area, own, regions) for own in mine))
