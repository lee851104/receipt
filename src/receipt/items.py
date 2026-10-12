"""What each signal shows as its purchases: three names at most, written so they never tell where someone shopped."""
import re

from .address import COUNTIES, COUNTY_CITIES, MUNICIPALITIES
from .attributes import has

LONGEST = 20  # letters a name keeps; a longer one is cut and ends with …
TOP = 3       # purchases listed per signal
# What a removed place name may leave behind: empty brackets, and separators at either edge.
EMPTY_BRACKETS = re.compile(r"\(\s*\)|（\s*）|\[\s*\]|【\s*】|「\s*」|『\s*』|〔\s*〕")
EDGES = re.compile(r"^[\s\-–—·・|/／,，、:：]+|[\s\-–—·・|/／,，、:：]+$")
# Tabs, line breaks and other control characters in a name become one space; the browser refuses names holding them.
SPACES = re.compile(r"[\s\x00-\x1f\x7f]+")


def place_words(rows, context):
    """Place names a purchase name may carry, longest first so 臺中市 goes before 臺中: cities and counties,
    county-administered cities, the person's own districts with and without 區, 鄉, 鎮 or 市, and the listed words."""
    words = set(context["vocabulary"]["place_words"])
    for city in (*MUNICIPALITIES, *COUNTIES, *COUNTY_CITIES):
        words.update((city, city[:-1]))
    for row in rows:
        local = (row.get("district") or "")[3:]
        if local:
            words.add(local)
            # A one-letter name such as 東 would cut far too much from ordinary names.
            if len(local) > 2:
                words.add(local[:-1])
    return sorted(words, key=lambda word: (-len(word), word))


def without_places(name, words):
    """The name with every place name taken out, reading 台 and 臺 alike."""
    for word in words:
        name = re.sub(re.escape(word.replace("台", "臺")).replace("臺", "[台臺]"), "", name)
    return name


def label(line, words, context):
    """How one purchase reads on the page: a hotel stay or a kind of ticket, or the name without its places."""
    vocabulary = context["vocabulary"]
    if line["channel"] == "住宿":
        return vocabulary["generic_labels"]["住宿"]
    if line["channel"] == "長途交通":
        text = line["name"] + line["merchant"]
        return next((kind for kind, keywords in vocabulary["transport_kinds"] if has(text, keywords)),
                    vocabulary["generic_labels"]["長途交通"])
    name = SPACES.sub(" ", line["name"]).strip().removeprefix("示範").strip()
    rest = without_places(name, words)
    # Only a removed place leaves anything to tidy; brackets, % or + in an ordinary name stay as they are.
    if rest != name:
        rest = EDGES.sub("", EMPTY_BRACKETS.sub("", rest))
    # Nothing but digits or marks left: say what kind of purchase it was instead.
    if not re.search(r"[^\W\d_]", rest):
        rest = context["report"]["categories"][line["category"]]["name"]
    return rest if len(rest) <= LONGEST else rest[:LONGEST - 1] + "…"


def listed(purchases, rows, context):
    """Each signal's three most bought names as [[name, bills], …], counting the bills a name is on, most first
    and ties by name; None for the signals that never list purchases."""
    words = place_words(rows, context)
    hidden = {signal["id"] for trait in context["traits"]["traits"] for signal in trait["signals"]
              if signal.get("list_items") is False}
    names = {}

    # One label per distinct purchase, however many signals list it.
    def named(line):
        key = (line["name"], line["channel"], line["category"], line["merchant"])
        if key not in names:
            names[key] = label(line, words, context)
        return names[key]

    lists = {}
    for key, lines in purchases.items():
        if key in hidden:
            lists[key] = None
            continue
        bills = {}
        for line in lines:
            bills.setdefault(named(line), set()).add(line["invoice"])
        ranked = sorted(bills.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        lists[key] = [[name, len(seen)] for name, seen in ranked[:TOP]]
    return lists
