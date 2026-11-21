"""The dating app's rules, with no database in sight: whose card someone may see, how a card reads (the score, what two
people share and where they differ), what to say first, and the fictional demo people's side of a chat.

Taste vectors are the 18 values of configs/traits.json: two-sided traits run from -1 (the first end) to +1 (the
second end), habits from 0 to 1, and None is unknown. They come from invoices (profiles.vector) or, until there are
enough invoices, from the taste quiz (dating_profiles.quiz)."""
import hashlib
import json
import random
from datetime import date

from ..receipt import similarity

# How strongly both must lean the same way before a trait counts as shared, or opposite ways before it counts as a
# difference: small values are close to "no preference" and would make empty claims.
LEAN = 0.15
HABIT = 0.3


def load_config(root):
    return json.loads((root / "configs" / "dating.json").read_text(encoding="utf-8"))


def ids(config, key):
    return [entry["id"] for entry in config[key]]


def age_of(birth_year, today=None):
    """Age in years from a birth year alone: the age reached this year. None without a birth year."""
    if birth_year is None:
        return None
    return (today or date.today()).year - birth_year


def interested(profile):
    return json.loads(profile.interested_in) if profile is not None else []


def missing(profile):
    """What a dating profile still needs before its owner can see cards or be seen: birth year, gender, and whom they
    want to meet. Everything else is optional."""
    if profile is None:
        return ["birth_year", "gender", "interested_in"]
    return [name for name, value in (("birth_year", profile.birth_year), ("gender", profile.gender),
                                     ("interested_in", interested(profile))) if not value]


def quiz_vector(profile, size):
    if profile is None or profile.quiz is None:
        return None
    vector = json.loads(profile.quiz)
    return vector if len(vector) == size else None


def taste(stored, profile, size):
    """(vector, source): the invoice taste when there is one, else the quiz's, else (None, None). source is "invoice"
    or "quiz", which the cards show as 發票認證 or 問卷自評."""
    if stored is not None and stored.vector is not None:
        vector = json.loads(stored.vector)
        if len(vector) == size:
            return vector, "invoice"
    vector = quiz_vector(profile, size)
    return (vector, "quiz") if vector is not None else (None, None)


def quiz_answers(values, settings, config):
    """The quiz's 18 values checked: two-sided answers from -1 to 1, habits from 0 to 1, None for a skipped question,
    and at least as many two-sided answers as a comparison needs. A ValueError says what is wrong."""
    traits = settings["traits"]
    if not isinstance(values, list) or len(values) != len(traits):
        raise ValueError(f"the quiz has {len(traits)} answers, one per trait")
    cleaned = []
    for trait, value in zip(traits, values):
        if value is None:
            cleaned.append(None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            raise ValueError(f"{trait['id']} must be a number or null")
        low = -1 if trait["kind"] == "two_sided" else 0
        if not low <= value <= 1:
            raise ValueError(f"{trait['id']} must be from {low} to 1")
        cleaned.append(round(float(value), 4))
    answered = sum(1 for trait, value in zip(traits, cleaned) if value is not None and trait["kind"] == "two_sided")
    needed = settings["similarity"]["min_shared_two_sided"]
    if answered < needed:
        raise ValueError(f"answer at least {needed} of the two-sided questions")
    return cleaned


def wants(seeker, seeker_age, other, other_age):
    """Whether seeker wants to meet other: other's gender is one seeker asked for and other's age is in seeker's
    range. seeker_age is unused, but kept so the call reads the same from both sides."""
    return (other.gender in interested(seeker) and other_age is not None
            and seeker.age_min <= other_age <= seeker.age_max)


def mutual(mine, my_age, theirs, their_age):
    return wants(mine, my_age, theirs, their_age) and wants(theirs, their_age, mine, my_age)


def band(percent, config):
    """The words and tone a score is shown with: 很合拍 (similar), 各有特色 (neutral), 有點互補 (opposite)..."""
    if percent is None:
        return {"label": "還看不出來", "tone": "neutral"}
    for entry in config["bands"]:
        if percent >= entry["min"]:
            return {"label": entry["label"], "tone": entry["tone"]}
    return {"label": config["bands"][-1]["label"], "tone": config["bands"][-1]["tone"]}


def side(trait, value):
    """The end of a two-sided trait a value leans to: 0 for the first, 1 for the second."""
    return 0 if value < 0 else 1


def highlights(mine, theirs, settings, parts):
    """What two people share and where they differ, strongest first. Each entry names the trait, a short word for it
    and the trait's own line (configs/traits.json "lines"), with its share of the score when the two are comparable.

    Shared: both lean the same way on a two-sided trait, or both have a habit. Different: they lean opposite ways."""
    alike, contrast = [], []
    if mine is None or theirs is None:
        return {"alike": alike, "contrast": contrast}
    for index, trait in enumerate(settings["traits"]):
        a, b = mine[index], theirs[index]
        if a is None or b is None:
            continue
        part = None if parts is None else parts[index]
        if trait["kind"] == "two_sided":
            if abs(a) < LEAN or abs(b) < LEAN:
                continue
            if side(trait, a) == side(trait, b):
                end = side(trait, a)
                alike.append({"trait": trait["id"], "end": end, "word": trait["ends"][end],
                              "line": trait["lines"]["both"][end], "part": part, "strength": min(abs(a), abs(b))})
            else:
                contrast.append({"trait": trait["id"], "mine": trait["ends"][side(trait, a)],
                                 "theirs": trait["ends"][side(trait, b)], "their_end": side(trait, b),
                                 "line": trait["lines"]["split"], "part": part, "strength": min(abs(a), abs(b))})
        elif a >= HABIT and b >= HABIT:
            alike.append({"trait": trait["id"], "word": trait["habit"], "line": trait["lines"]["both"],
                          "part": part, "strength": min(a, b)})
    alike.sort(key=lambda entry: -(entry["part"] if entry["part"] is not None else entry["strength"]))
    contrast.sort(key=lambda entry: entry["part"] if entry["part"] is not None else -entry["strength"])
    for entry in alike + contrast:
        entry.pop("strength")
        if entry["part"] is not None:
            entry["part"] = round(entry["part"], 4)
    return {"alike": alike, "contrast": contrast}


def keywords(vector, settings, limit=3):
    """The words that describe someone best: the end of each strong two-sided trait and each strong habit."""
    if vector is None:
        return []
    found = []
    for trait, value in zip(settings["traits"], vector):
        if value is None:
            continue
        if trait["kind"] == "two_sided" and abs(value) >= 0.3:
            found.append((abs(value), trait["ends"][side(trait, value)]))
        elif trait["kind"] == "level" and value >= 0.4:
            found.append((value, trait["habit"]))
    found.sort(key=lambda pair: -pair[0])
    return [word for _, word in found[:limit]]


def score(mine, theirs, model):
    """compare()'s answer with the whole percentage the app shows, None when the two cannot be compared."""
    result = similarity.compare(mine, theirs, model)
    percent = similarity.percent(result["score"]) if result["comparable"] else None
    return result, percent


def contributions(parts, settings):
    """Each trait's share of the score, biggest effect first, for the "why this score" bars."""
    if parts is None:
        return []
    rows = [{"trait": trait["id"], "part": round(part, 4)} for trait, part in zip(settings["traits"], parts)
            if part is not None and round(part, 4) != 0]  # a habit neither has adds nothing worth a bar
    rows.sort(key=lambda row: -abs(row["part"]))
    return rows


def question_for(config, trait_id, end=None):
    """The opener question for a trait: a habit has one, a two-sided trait one per end (asked of that end)."""
    question = config.get("icebreakers", {}).get(trait_id)
    if isinstance(question, list):
        return question[end] if end is not None and end < len(question) else None
    return question


def icebreakers(found, config, limit=3):
    """Openers that start from what the two have in common, then one from a difference (asking about their side),
    then friendly defaults."""
    lines = []
    for entry in found["alike"]:
        question = question_for(config, entry["trait"], entry.get("end"))
        if question:
            lines.append(f"我們都是「{entry['word']}」！{question}")
    for entry in found["contrast"][:1]:
        question = question_for(config, entry["trait"], entry.get("their_end"))
        if question:
            lines.insert(min(1, len(lines)), f"你{entry['theirs']}、我{entry['mine']}，剛好相反 😆 {question}")
    lines += config.get("default_icebreakers", [])
    return lines[:limit]


def seeded(*parts):
    """A random generator that gives the same answers for the same parts, so demo people behave the same each run."""
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def demo_likes_back(demo_id, liker_id, percent):
    """Whether a fictional demo person likes someone back: always when the two are clearly alike or clearly opposite,
    else half the time, the same way on every run."""
    if percent is None:
        return False
    if percent >= 10 or percent <= -10:
        return True
    return seeded("like", demo_id, liker_id).random() < 0.5


def demo_reply(config, text, sent_before, found, name, percent, match_id):
    """What a fictional demo person answers to a message: a greeting to the first one, an answer to a question, a
    word about something the two share, or a friendly follow-up."""
    replies = config["demo"]["replies"]
    rng = seeded("reply", match_id, sent_before, text)
    values = {"name": name, "percent": "?" if percent is None else f"{percent:+d}%"}
    asked = any(mark in text for mark in ("?", "？", "嗎", "呢"))
    if sent_before == 0:
        template = rng.choice(replies["opening"])
        if asked:  # a first message that asks something gets its answer after the greeting
            template += "\n" + rng.choice(replies["question"])
    elif asked:
        template = rng.choice(replies["question"])
    elif found["alike"] and rng.random() < 0.5:
        values["line"] = rng.choice(found["alike"])["line"]
        template = rng.choice(replies["alike"])
    else:
        template = rng.choice(replies["generic"])
    return template.format(**values)


def demo_profile(user, stored, config, regions, today=None):
    """A fictional dating profile for a demo user, the same on every run: a name, age, gender, city from their
    invoices' home district, a bio for their persona, and whom they want to meet (wide, so they meet most people)."""
    demo = config["demo"]
    rng = seeded("profile", demo["seed"], user.id)
    gender = rng.choices(["female", "male", "nonbinary"], weights=[48, 46, 6])[0]
    if gender == "nonbinary":
        wanted = ["female", "male", "nonbinary"]
    else:
        other = "male" if gender == "female" else "female"
        wanted = rng.choices([[other], [other, gender], [gender]], weights=[82, 14, 4])[0]
        if rng.random() < 0.5:
            wanted = sorted(set(wanted) | {"nonbinary"})
    persona = demo["personas"].get(user.persona or "", {})
    areas = json.loads(stored.areas) if stored is not None else []
    city = areas[0][:3] if areas and areas[0][:3] in regions else None
    year = (today or date.today()).year
    return {"nickname": rng.choice(demo["names"][gender]), "birth_year": year - rng.randint(22, 38),
            "gender": gender, "interested_in": json.dumps(wanted), "age_min": 18, "age_max": 60, "city": city,
            "bio": rng.choice(persona.get("bios", ["你好！"])), "intent": rng.choice(ids(config, "intents")),
            "emoji": persona.get("emoji", "🙂"), "discoverable": True}


# Photos -------------------------------------------------------------------------------------------------------------

START_OF_FRAME = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
DROPPED = set(range(0xE1, 0xF0)) | {0xFE}  # APP1-APP15 (EXIF with GPS, XMP, maker notes...) and comments


def clean_jpeg(data, max_side):
    """The JPEG with its metadata segments taken out, so no camera, time or GPS location goes along; its size is
    checked from the frame header. A ValueError for anything that is not a whole baseline or progressive JPEG."""
    if not data.startswith(b"\xff\xd8\xff"):
        raise ValueError("not a JPEG")
    out, index, size, end = bytearray(b"\xff\xd8"), 2, None, len(data)
    while index < end:
        if data[index] != 0xFF:
            raise ValueError("broken JPEG")
        while index < end and data[index] == 0xFF:
            index += 1
        if index >= end:
            raise ValueError("broken JPEG")
        marker = data[index]
        index += 1
        if marker == 0xD9:
            if size is None:
                raise ValueError("a JPEG without a frame")
            out += b"\xff\xd9"
            return bytes(out), size
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            out += bytes((0xFF, marker))
            continue
        if index + 2 > end:
            raise ValueError("broken JPEG")
        length = int.from_bytes(data[index:index + 2], "big")
        if length < 2 or index + length > end:
            raise ValueError("broken JPEG")
        segment = data[index:index + length]
        index += length
        if marker in START_OF_FRAME:
            if length < 8:
                raise ValueError("broken JPEG")
            height, width = int.from_bytes(segment[3:5], "big"), int.from_bytes(segment[5:7], "big")
            if not (0 < width <= max_side and 0 < height <= max_side):
                raise ValueError(f"the photo must be at most {max_side} pixels on each side")
            size = (width, height)
        if marker in DROPPED:
            continue
        out += bytes((0xFF, marker)) + segment
        if marker == 0xDA:  # the compressed picture runs to the next marker that is not a stuffed byte or a restart
            scan = index
            while True:
                found = data.find(b"\xff", scan)
                if found < 0 or found + 1 >= end:
                    raise ValueError("broken JPEG")
                following = data[found + 1]
                if following == 0x00 or 0xD0 <= following <= 0xD7 or following == 0xFF:
                    scan = found + 1
                    continue
                break
            out += data[index:found]
            index = found
    raise ValueError("broken JPEG")
