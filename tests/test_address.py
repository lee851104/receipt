"""Address reduction keeps only city and district; every street here is fictional."""
import unittest

from src.receipt.address import normalize_place, parse_district


class AddressTests(unittest.TestCase):
    def test_postal_code_and_municipality_district(self):
        self.assertEqual(parse_district("802高雄市苓雅區示範路1號"), "高雄市苓雅區")

    def test_variant_character_becomes_formal(self):
        self.assertEqual(parse_district("台北市信義區示範路2號"), "臺北市信義區")

    def test_spaces_are_ignored_and_municipal_districts_end_with_qu(self):
        # 前鎮區 contains 鎮, so a municipality must read on until 區.
        self.assertEqual(parse_district("806 高雄市前　鎮區示範路3號"), "高雄市前鎮區")

    def test_county_district_ends_with_township_or_city(self):
        self.assertEqual(parse_district("新竹縣竹北市示範路4號"), "新竹縣竹北市")
        self.assertEqual(parse_district("臺灣省屏東縣東港鎮示範路5號"), "屏東縣東港鎮")

    def test_county_city_without_county_gets_its_county(self):
        self.assertEqual(parse_district("宜蘭市示範路6號"), "宜蘭縣宜蘭市")

    def test_unreadable_addresses_return_none(self):
        for address in (None, "", "PRIVATE-ADDRESS", "高雄市", "海外示範地址"):
            self.assertIsNone(parse_district(address), address)

    def test_normalize_place_unifies_spacing_and_variant(self):
        self.assertEqual(normalize_place(" 台灣 中油 "), "臺灣中油")


if __name__ == "__main__":
    unittest.main()
