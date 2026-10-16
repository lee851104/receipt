"""Who the match list shows: comparable people scored against me, past the bar on one side, within a distance."""
import json
import math
import unittest
from pathlib import Path

from src.api import matching
from src.api.db import ROOT
from src.receipt import similarity
from src.receipt.build import drawing_of, trait_network_data
from src.receipt.places import load_regions
from src.receipt.traits import load_context, signal_ids, similarity_model

CONTEXT = load_context(ROOT)
MODEL = similarity_model(CONTEXT["traits"])
MATCH = CONTEXT["traits"]["match"]  # min_score 0.3, opposite_score 0.1, top 5
REGIONS = load_regions(ROOT)
SIZE = len(MODEL["cells"])
# The first five two-sided cells: just enough shared two-sided cells for two people to be comparable.
FIVE = [index for index, cell in enumerate(MODEL["cells"]) if cell["kind"] == "two_sided"][:5]
ME = [1.0 if index in FIVE else None for index in range(SIZE)]


def scoring(score):
    """A vector that scores about `score` against ME: t on ME's five cells gives 5t / (5|t| + 0.25)."""
    t = 0.25 * score / (5 * (1 - abs(score)))
    return [t if index in FIVE else None for index in range(SIZE)]


def person(user_id, vector, areas=(), name=None):
    return {"user_id": user_id, "display_name": name or f"P{user_id}", "vector": vector, "areas": list(areas)}


def entry(user_id, score, name=None, distance=None):
    """A scored entry shaped as entries() makes it, for pick()."""
    return {"user_id": user_id, "display_name": name or f"P{user_id}", "score": score,
            "percent": similarity.percent(score), "area": None, "distance": distance}


class EntriesTests(unittest.TestCase):
    def test_each_comparable_person_gets_the_score_compare_gives(self):
        [scored] = matching.entries(ME, [], [person(2, scoring(0.6))], MODEL, REGIONS)
        self.assertEqual(scored["score"], similarity.compare(ME, scoring(0.6), MODEL)["score"])
        self.assertAlmostEqual(scored["score"], 0.6)
        self.assertEqual(scored["percent"], 60)

    def test_people_who_cannot_be_compared_are_left_out(self):
        four = scoring(0.6)
        four[FIVE[4]] = None  # only four shared two-sided cells
        people = [person(2, None), person(3, four), person(4, scoring(0.6))]
        self.assertEqual([scored["user_id"] for scored in matching.entries(ME, [], people, MODEL, REGIONS)], [4])

    def test_an_entry_shows_only_the_id_name_score_percent_area_and_distance(self):
        people = [person(2, scoring(0.6), ["臺北市信義區"], "Ben")]
        [scored] = matching.entries(ME, ["臺北市大安區"], people, MODEL, REGIONS)
        self.assertEqual(scored, {"user_id": 2, "display_name": "Ben", "score": scored["score"], "percent": 60,
                                  "area": "臺北市信義區", "distance": 1})

    def test_the_area_is_their_home_district_closest_to_mine(self):
        people = [person(2, scoring(0.6), ["高雄市前鎮區", "臺北市信義區"])]
        [scored] = matching.entries(ME, ["臺北市大安區"], people, MODEL, REGIONS)
        self.assertEqual((scored["area"], scored["distance"]), ("臺北市信義區", 1))

    def test_the_distance_is_unknown_when_either_side_has_no_home_district(self):
        cases = [([], ["高雄市前鎮區"], "高雄市前鎮區"), (["臺北市大安區"], [], None), ([], [], None)]
        for mine, theirs, area in cases:
            with self.subTest(mine=mine, theirs=theirs):
                [scored] = matching.entries(ME, mine, [person(2, scoring(0.6), theirs)], MODEL, REGIONS)
                self.assertEqual((scored["area"], scored["distance"]), (area, None))

    def test_people_keep_their_order(self):
        people = [person(3, scoring(0.2)), person(2, scoring(0.9)), person(4, scoring(-0.5))]
        self.assertEqual([scored["user_id"] for scored in matching.entries(ME, [], people, MODEL, REGIONS)], [3, 2, 4])


class PickTests(unittest.TestCase):
    def pick(self, entries, kind="similar", level=None):
        return matching.pick(entries, kind, level, MATCH)

    def ids(self, result):
        return [chosen["user_id"] for chosen in result["people"]]

    def test_each_scope_allows_a_farthest_distance(self):
        self.assertEqual(matching.SCOPES, {"all": None, "district": 0, "city": 1, "region": 2})

    def test_similar_people_need_a_whole_percentage_of_at_least_30(self):
        result = self.pick([entry(2, 0.31), entry(3, 0.295), entry(4, 0.2949), entry(5, -0.5), entry(6, 0.0)])
        self.assertEqual(self.ids(result), [2, 3])  # 0.295 prints as +30%, 0.2949 as +29%
        self.assertEqual(result["eligible"], 2)

    def test_opposite_people_need_a_whole_percentage_of_at_most_minus_10(self):
        entries = [entry(2, -0.42), entry(3, -0.0951), entry(4, -0.095), entry(5, 0.6), entry(6, 0.0)]
        result = self.pick(entries, "opposite")
        self.assertEqual(self.ids(result), [2, 3])  # -0.0951 prints as -10%, -0.095 as -9% (halves go up)
        self.assertEqual(result["eligible"], 2)

    def test_someone_opposite_is_not_similar(self):
        entries = [entry(2, -0.42)]
        self.assertEqual((self.ids(self.pick(entries)), self.ids(self.pick(entries, "opposite"))), ([], [2]))

    def test_similar_goes_from_the_highest_score_and_opposite_from_the_lowest(self):
        entries = [entry(2, 0.4), entry(3, 0.9), entry(4, 0.6), entry(5, -0.3), entry(6, -0.8), entry(7, -0.5)]
        self.assertEqual(self.ids(self.pick(entries)), [3, 4, 2])
        self.assertEqual(self.ids(self.pick(entries, "opposite")), [6, 7, 5])

    def test_ties_go_by_display_name_in_code_point_order_then_by_user_id(self):
        # Code points: upper case before lower case, Latin before Chinese.
        names = [(2, "咖啡"), (3, "amy"), (4, "Bob"), (5, "amy"), (1, "amy")]
        for score, kind in ((0.5, "similar"), (-0.5, "opposite")):
            with self.subTest(kind=kind):
                entries = [entry(user_id, score, name) for user_id, name in names]
                self.assertEqual(self.ids(self.pick(entries, kind)), [4, 1, 3, 5, 2])

    def test_only_the_top_five_are_shown_but_every_eligible_person_is_counted(self):
        entries = [entry(user_id, 0.3 + user_id / 100) for user_id in range(2, 10)]  # eight people past +30%
        result = self.pick(entries)
        self.assertEqual((result["eligible"], result["within"], self.ids(result)), (8, 8, [9, 8, 7, 6, 5]))

    def test_each_scope_keeps_the_people_at_most_that_far_away(self):
        entries = [entry(2, 0.5, distance=0), entry(3, 0.6, distance=1), entry(4, 0.7, distance=2),
                   entry(5, 0.8, distance=3), entry(6, 0.9, distance=None)]
        for level, ids in ((None, [6, 5, 4, 3, 2]), (0, [2]), (1, [3, 2]), (2, [4, 3, 2])):
            with self.subTest(level=level):
                result = self.pick(entries, level=level)
                self.assertEqual((result["eligible"], result["within"], self.ids(result)), (5, len(ids), ids))

    def test_the_distance_never_changes_who_is_past_the_bar(self):
        result = self.pick([entry(2, 0.5, distance=3), entry(3, 0.2, distance=0)], level=0)
        self.assertEqual((result["eligible"], result["within"], self.ids(result)), (1, 0, []))

    def test_a_kind_other_than_similar_or_opposite_is_refused_not_taken_for_similar(self):
        for kind in ("close", "Similar", "", None):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    self.pick([entry(2, 0.5)], kind)

    def test_the_chosen_entries_come_back_unchanged(self):
        chosen = entry(2, 0.5, distance=1)
        self.assertEqual(self.pick([dict(chosen)])["people"], [chosen])


FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "similarity-cases.json").read_text(encoding="utf-8"))
TOTALS = ("dot", "norm_mine", "norm_theirs", "shrink", "denominator", "score", "percent")


class BreakdownTests(unittest.TestCase):
    def test_every_shared_case_takes_the_score_apart_as_compare_does(self):
        for case in FIXTURE["cases"]:
            with self.subTest(case=case["name"]):
                result = matching.breakdown(case["mine"], case["theirs"], case.get("model", FIXTURE["model"]))
                self.assertEqual(result["comparable"], case["comparable"])
                if not case["comparable"]:
                    continue
                self.assertAlmostEqual(result["score"], case["score"], places=9)
                for cell, part in zip(result["cells"], case["parts"], strict=True):
                    if part is None:
                        self.assertIsNone(cell["part"])
                    else:
                        self.assertAlmostEqual(cell["part"], part, places=9)

    def test_the_parts_add_up_to_the_score_exactly_and_the_score_is_compares(self):
        for case in FIXTURE["cases"]:
            model = case.get("model", FIXTURE["model"])
            result = matching.breakdown(case["mine"], case["theirs"], model)
            if result["comparable"]:
                with self.subTest(case=case["name"]):
                    self.assertEqual(sum(cell["part"] for cell in result["cells"] if cell["part"] is not None),
                                     result["score"])
                    self.assertEqual(result["score"], similarity.compare(case["mine"], case["theirs"], model)["score"])
                    self.assertEqual(result["percent"], similarity.percent(result["score"]))

    def test_each_number_follows_the_formula(self):
        mine, theirs = [0.6, None, 0.2, 0.8, -0.2, 0.5, 0.3], [0.5, 0.9, 0.1, 0.7, -0.1, 0.4, 0.0]
        result = matching.breakdown(mine, theirs, FIXTURE["model"])
        shared = [0, 2, 3, 4, 5, 6]
        self.assertEqual([cell["shared"] for cell in result["cells"]], [True, False, True, True, True, True, True])
        self.assertEqual([cell["product"] for cell in result["cells"]],
                         [None if index not in shared else mine[index] * theirs[index] for index in range(7)])
        self.assertEqual(result["dot"], sum(mine[index] * theirs[index] for index in shared))
        self.assertEqual(result["norm_mine"], math.sqrt(sum(mine[index] ** 2 for index in shared)))
        self.assertEqual(result["norm_theirs"], math.sqrt(sum(theirs[index] ** 2 for index in shared)))
        self.assertEqual(result["shrink"], 0.25)
        self.assertEqual(result["denominator"], result["norm_mine"] * result["norm_theirs"] + 0.25)
        self.assertAlmostEqual(result["score"], result["dot"] / result["denominator"], places=12)
        self.assertEqual((result["shared_two_sided"], result["min_shared_two_sided"]), (5, 5))
        self.assertIsNone(result["reason"])

    def test_each_cell_shows_its_values_weight_and_share_and_nothing_else(self):
        [cell] = matching.breakdown(ME, scoring(0.6), MODEL)["cells"][:1]
        self.assertEqual(set(cell), {"id", "kind", "mine", "theirs", "weight", "shared", "product", "part"})
        self.assertEqual((cell["id"], cell["kind"], cell["weight"]), (MODEL["cells"][0]["id"], MODEL["cells"][0]["kind"], 1))

    def test_too_few_shared_two_sided_cells_give_no_numbers_at_all(self):
        four = scoring(0.6)
        four[FIVE[4]] = None
        result = matching.breakdown(ME, four, MODEL)
        self.assertEqual((result["comparable"], result["reason"], result["shared_two_sided"]), (False, "too_few_shared", 4))
        self.assertEqual({key: result[key] for key in TOTALS}, dict.fromkeys(TOTALS))
        self.assertTrue(all(cell["product"] is None and cell["part"] is None for cell in result["cells"]))
        self.assertEqual([cell["shared"] for cell in result["cells"]].count(True), 4)

    def test_without_a_vector_on_either_side_there_is_not_enough_data(self):
        for mine, theirs in ((None, scoring(0.6)), (ME, None), (None, None)):
            with self.subTest(mine=mine is None, theirs=theirs is None):
                result = matching.breakdown(mine, theirs, MODEL)
                self.assertEqual((result["comparable"], result["reason"], result["shared_two_sided"]),
                                 (False, "not_enough_items", 0))
                self.assertEqual({key: result[key] for key in TOTALS}, dict.fromkeys(TOTALS))
                self.assertEqual(len(result["cells"]), SIZE)
                self.assertFalse(any(cell["shared"] for cell in result["cells"]))
                if mine is None:
                    self.assertTrue(all(cell["mine"] is None for cell in result["cells"]))


class NetworkTests(unittest.TestCase):
    def explained(self):
        """A made-up traits.explain answer: every push 0.1, every signal 1, no purchases listed."""
        settings = CONTEXT["traits"]
        return {"vector": scoring(0.6), "pushes": [[0.1] * len(trait["signals"]) for trait in settings["traits"]],
                "signals": dict.fromkeys(signal_ids(settings), 1.0), "items": dict.fromkeys(signal_ids(settings))}

    def test_it_is_the_v1_network_data_with_mine_and_theirs_instead_of_friends(self):
        settings = CONTEXT["traits"]
        data = matching.network(settings, {"mine": (ME, self.explained()), "theirs": (None, None)})
        v1 = trait_network_data(settings, {}, [])
        self.assertEqual(set(data), set(v1) - {"friends"} | {"mine", "theirs"})
        self.assertEqual({key: data[key] for key in v1 if key != "friends"}, {key: v1[key] for key in v1 if key != "friends"})

    def test_a_side_shows_the_vector_worked_out_now_with_its_drawing_not_the_stored_one(self):
        settings = CONTEXT["traits"]
        explained = self.explained()
        self.assertNotEqual(explained["vector"], ME)  # the stored vector and the one worked out now tell apart
        data = matching.network(settings, {"mine": (ME, explained), "theirs": (None, None)})
        self.assertEqual(data["mine"], {"vector": explained["vector"], **drawing_of(explained, signal_ids(settings))})

    def test_a_side_without_a_stored_vector_or_a_taste_now_is_all_null(self):
        settings = CONTEXT["traits"]
        empty = {"vector": None, "pushes": None, "signals": None, "items": None}
        for side in ((None, None), (None, self.explained()), (ME, None)):
            with self.subTest(vector=side[0] is not None, explained=side[1] is not None):
                self.assertEqual(matching.network(settings, {"mine": side, "theirs": side})["theirs"], empty)

    def test_theirs_is_drawn_exactly_like_mine_with_nothing_left_out(self):
        settings = CONTEXT["traits"]
        order = signal_ids(settings)
        # Every signal and every push has a value of its own, so anything left out or moved shows.
        explained = self.explained()
        explained["signals"] = {key: float(number) for number, key in enumerate(order, 1)}
        count = iter(range(1, 1000))
        explained["pushes"] = [[next(count) / 1000 for _ in trait["signals"]] for trait in settings["traits"]]
        data = matching.network(settings, {"mine": (ME, explained), "theirs": (ME, explained)})
        drawn = {"vector": explained["vector"], **drawing_of(explained, order)}
        self.assertEqual(data["theirs"], drawn)
        self.assertEqual(data["mine"], drawn)
        self.assertFalse(any(value is None for value in data["theirs"]["signals"]))
        self.assertFalse(any(value is None for pushes in data["theirs"]["pushes"] for value in pushes))


if __name__ == "__main__":
    unittest.main()
