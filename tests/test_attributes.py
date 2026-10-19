"""Item and shop attributes read from fictional names."""
import json
import unittest
from pathlib import Path

from src.receipt.attributes import channel_of, describe

ROOT = Path(__file__).resolve().parents[1]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
WORDS = json.loads((ROOT / "configs" / "attributes.json").read_text(encoding="utf-8"))


def line(name, category, merchant="測試小店", quantity=1):
    row = {"name": name, "category": category, "merchant": merchant, "quantity": quantity}
    return describe(row, channel_of(merchant, BRANDS, WORDS), WORDS)


class AttributeTests(unittest.TestCase):
    def test_every_brand_names_a_channel(self):
        channels = {"超商", "量販", "超市", "咖啡", "手搖", "餐飲", "3C", "選物", "寵物", "娛樂", "長途交通", "加油", "停車",
                    "住宿", "酒吧", "運動", "一般店家"}
        self.assertTrue(all(entry["channel"] in channels for entry in BRANDS))
        self.assertTrue(all(entry["channel"] in channels for entry in WORDS["seller_channels"]))

    def test_brand_list_decides_before_seller_words(self):
        self.assertEqual(channel_of("統一超商股份有限公司高雄示範分公司", BRANDS, WORDS), "超商")
        self.assertEqual(channel_of("台灣中油股份有限公司", BRANDS, WORDS), "加油")
        # 示範客運 is a listed city shuttle, although 客運 alone means a long-distance bus.
        self.assertEqual(channel_of("示範客運", BRANDS, WORDS), "一般店家")
        self.assertEqual(channel_of("測試客運股份有限公司", BRANDS, WORDS), "長途交通")
        self.assertEqual(channel_of("測試動物醫院", BRANDS, WORDS), "寵物")
        self.assertEqual(channel_of("測試 bar", BRANDS, WORDS), "酒吧")
        self.assertEqual(channel_of("測試小店", BRANDS, WORDS), "一般店家")

    def test_sugar_comes_from_words_then_drink_kind_then_tea_shop(self):
        self.assertEqual(line("測試半糖綠茶", 1)["sugar"], 0.5)
        self.assertEqual(line("測試無糖拿鐵", 1)["sugar"], 0)
        self.assertEqual(line("測試鮮奶", 1)["sugar"], 0.2)
        self.assertEqual(line("測試冰美式", 1)["sugar"], 0)
        self.assertEqual(line("測試珍珠鮮奶", 1)["sugar"], 1)
        self.assertEqual(line("測試青茶", 1, merchant="示範茶屋")["sugar"], 1)
        self.assertIsNone(line("測試手沖咖啡", 1)["sugar"])
        self.assertIsNone(line("測試半糖布丁", 2)["sugar"])

    def test_fruit_is_not_cooking_and_rice_wine_is_not_alcohol(self):
        self.assertTrue(line("測試高麗菜", 3)["cooking"])
        self.assertFalse(line("測試香蕉", 3)["cooking"])
        self.assertTrue(line("測試料理米酒", 3)["kitchen"])
        self.assertFalse(line("測試料理米酒", 3)["alcohol"])
        self.assertFalse(line("測試無糖綠茶", 1)["kitchen"])
        self.assertTrue(line("測試生啤酒", 1)["alcohol"])
        self.assertFalse(line("測試酒釀湯圓", 2)["alcohol"])

    def test_pet_items_carry_their_species(self):
        self.assertEqual((line("測試貓砂", 8)["pet_supply"], line("測試貓砂", 8)["species"]), (True, "cat"))
        self.assertEqual((line("測試犬用飼料", 8)["pet_food"], line("測試犬用飼料", 8)["species"]), (True, "dog"))
        self.assertEqual((line("測試寵物罐頭", 8)["pet_food"], line("測試寵物罐頭", 8)["species"]), (True, None))

    def test_quick_meals_bulk_fun_and_home_goods(self):
        self.assertTrue(line("測試鮪魚飯糰", 0)["quick"])
        self.assertFalse(line("測試鮪魚飯糰", 2)["quick"])
        self.assertTrue(line("測試即期便當", 0)["clearance"])
        self.assertTrue(line("測試衛生紙箱", 8)["bulk"])
        self.assertTrue(line("測試洗碗精3入", 8)["bulk"])
        self.assertTrue(line("測試洗碗精", 8, quantity=3)["bulk"])
        self.assertFalse(line("測試洗碗精", 8)["bulk"])
        self.assertEqual(line("測試爆米花", 2, merchant="測試影城")["fun"], "電影")
        self.assertEqual(line("測試展覽門票", 5)["fun"], "展演")
        self.assertTrue(line("測試香氛蠟燭", 8)["home"])
        self.assertFalse(line("測試大杯紅茶", 1)["home"])
        self.assertTrue(line("測試手帳", 8)["stationery"])


if __name__ == "__main__":
    unittest.main()
