"""Home districts and how far apart two people live, from fictional bills."""
import unittest
from datetime import date
from pathlib import Path

from src.receipt.places import areas_of, closest_area, distance, load_regions, place_distance
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
REGIONS = load_regions(ROOT)


def bills(*groups):
    """One paid bill per entry, from (count, district, merchant) groups."""
    rows = []
    for count, district, merchant in groups:
        for _ in range(count):
            rows.append({"date": date(2026, 3, 2), "day": 2, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": "測試便當", "quantity": 1, "amount": 100, "category": 0,
                         "provisional": False})
    return rows


class AreaTests(unittest.TestCase):
    def test_home_districts_hold_a_fifth_of_located_bills_two_at_most(self):
        rows = bills((6, "高雄市苓雅區", "測試便當店"), (3, "高雄市新興區", "測試便當店"), (1, "屏東縣恆春鎮", "測試海港餐廳"))
        self.assertEqual(areas_of(rows, CONTEXT), ["高雄市苓雅區", "高雄市新興區"])
        # Equal counts fall back to the district name, so the order never depends on the input.
        rows = bills((4, "臺北市信義區", "測試便當店"), (3, "臺北市內湖區", "測試便當店"), (3, "新北市板橋區", "測試便當店"))
        self.assertEqual(areas_of(rows, CONTEXT), ["臺北市信義區", "新北市板橋區"])

    def test_online_sellers_and_bills_without_a_district_do_not_count(self):
        rows = bills((3, "高雄市苓雅區", "測試便當店"), (5, "臺北市信義區", "蝦皮購物"), (4, None, "測試小店"))
        self.assertEqual(areas_of(rows, CONTEXT), ["高雄市苓雅區"])

    def test_nobody_reaching_a_fifth_leaves_no_home(self):
        districts = ["高雄市苓雅區", "高雄市新興區", "高雄市前鎮區", "高雄市左營區", "臺北市信義區", "臺北市內湖區"]
        self.assertEqual(areas_of(bills(*[(1, district, "測試便當店") for district in districts]), CONTEXT), [])


class DistanceTests(unittest.TestCase):
    def test_four_distances(self):
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市苓雅區", REGIONS), 0)
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市左營區", REGIONS), 1)
        self.assertEqual(place_distance("高雄市苓雅區", "屏東縣恆春鎮", REGIONS), 2)
        self.assertEqual(place_distance("高雄市苓雅區", "臺北市信義區", REGIONS), 3)
        # Two cities missing from the table do not count as one region.
        self.assertEqual(place_distance("高雄市苓雅區", "臺北市信義區", {}), 3)

    def test_cards_show_their_district_closest_to_mine(self):
        mine = ["高雄市苓雅區", "高雄市新興區"]
        self.assertEqual(closest_area(mine, ["高雄市前鎮區", "高雄市苓雅區"], REGIONS), "高雄市苓雅區")
        # Equally far districts keep their own order.
        self.assertEqual(closest_area(["臺北市信義區"], ["高雄市前鎮區", "高雄市苓雅區"], REGIONS), "高雄市前鎮區")
        self.assertEqual(closest_area([], ["高雄市前鎮區", "高雄市苓雅區"], REGIONS), "高雄市前鎮區")
        self.assertIsNone(closest_area(mine, [], REGIONS))

    def test_the_closest_pair_counts_and_no_home_is_far(self):
        self.assertEqual(distance(["臺北市信義區", "高雄市新興區"], ["高雄市苓雅區"], REGIONS), 1)
        self.assertEqual(distance([], ["高雄市苓雅區"], REGIONS), 3)
        self.assertEqual(distance(["高雄市苓雅區"], [], REGIONS), 3)

    def test_regions_come_from_their_own_config(self):
        self.assertEqual(REGIONS["高雄市"], "南部")
        self.assertEqual(REGIONS["新竹縣"], "北部")
        self.assertEqual(len(REGIONS), 22)
        # Districts are matched to cities by their first three characters, so every city name must be three long.
        self.assertTrue(all(len(city) == 3 for city in REGIONS))


if __name__ == "__main__":
    unittest.main()
