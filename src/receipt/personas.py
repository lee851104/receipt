"""Deterministic fictional people to match against; every shop and person here is made up."""
import random

SEED = 20261007
MONTHS = ((2026, 3, 31), (2026, 4, 30))
LETTERS = "ABCDE"

# Habit: (category index, merchant, item names, (lowest, highest) amount, (fewest, most) visits a month).
# Item names given as {"veg": [...], "meat": [...]} differ between members listed in meat_members.
TYPES = [
    {"label": "咖啡上班族", "areas": {"臺北市信義區": 6, "臺北市內湖區": 4}, "habits": [
        (1, "示範咖啡", ["示範拿鐵", "示範美式"], (150, 220), (14, 18)),
        (0, "示範便當店", ["示範雞腿便當", "示範排骨便當"], (100, 140), (10, 13)),
        (2, "示範咖啡", ["示範可頌"], (160, 200), (3, 5)),
        (6, "示範捷運", ["示範捷運儲值"], (300, 500), (2, 3)),
    ]},
    {"label": "手搖學生", "areas": {"高雄市苓雅區": 6, "高雄市新興區": 4}, "meat_members": (3, 4), "habits": [
        (1, "示範茶屋", ["示範花果茶", "示範青茶"], (45, 75), (9, 12)),
        (0, "示範餐坊", {"veg": ["示範蔬食餐盒"], "meat": ["示範鮮蝦餐盒"]}, (95, 130), (9, 12)),
        (0, "示範水餃館", {"veg": ["示範蔬菜水餃"], "meat": ["示範鮮蝦水餃"]}, (70, 110), (2, 3)),
        (6, "示範客運", ["示範客運票"], (40, 60), (5, 7)),
        (2, "示範烘焙店", ["示範燕麥餅"], (70, 100), (3, 5)),
        (4, "示範運動館", ["示範體適能體驗票"], (80, 100), (2, 3)),
        (8, "示範生活館", ["示範文具組"], (60, 120), (1, 3)),
    ]},
    {"label": "健身族", "areas": {"高雄市前鎮區": 5, "高雄市苓雅區": 5}, "habits": [
        (4, "示範運動館", ["示範重訓課", "示範健身月票"], (300, 600), (6, 8)),
        (0, "示範餐坊", ["示範雞肉餐盒", "示範蔬食沙拉"], (120, 160), (8, 10)),
        (1, "示範超商", ["示範無糖豆漿", "示範乳清飲"], (35, 60), (8, 10)),
        (3, "示範量販", ["示範雞肉分裝包"], (200, 300), (2, 3)),
    ]},
    {"label": "自己下廚", "areas": {"新北市板橋區": 7, "臺北市內湖區": 3}, "habits": [
        (3, "示範量販", ["示範綜合蔬菜箱", "示範蔬菜組合"], (250, 400), (8, 10)),
        (3, "示範蔬果舖", ["示範當季蔬菜"], (80, 150), (4, 6)),
        (8, "示範量販", ["示範廚房紙巾", "示範洗碗精"], (80, 200), (3, 4)),
        (1, "示範超商", ["示範鮮奶"], (50, 90), (3, 5)),
        (0, "示範早餐店", ["示範蛋餅"], (40, 70), (3, 4)),
    ]},
    {"label": "3C 玩家", "areas": {"高雄市苓雅區": 10}, "habits": [
        (9, "示範數位店", ["示範機械鍵盤", "示範耳機", "示範傳輸線", "示範行動電源"], (300, 2500), (6, 8)),
        (0, "示範速食店", ["示範雞排堡", "示範牛肉堡"], (120, 200), (4, 6)),
        (1, "示範超商", ["示範能量飲"], (40, 70), (2, 3)),
        (2, "示範超商", ["示範洋芋片"], (40, 80), (1, 2)),
    ]},
    {"label": "旅行族", "areas": {"屏東縣恆春鎮": 5, "宜蘭縣宜蘭市": 5}, "habits": [
        (7, "示範旅宿", ["示範旅店雙人房"], (1800, 3200), (2, 3)),
        (6, "示範高鐵", ["示範高鐵車票"], (700, 1500), (2, 4)),
        (0, "示範海港餐廳", ["示範海鮮套餐", "示範燒肉套餐"], (450, 900), (4, 6)),
        (1, "示範超商", ["示範礦泉水"], (20, 40), (2, 4)),
        (2, "示範超商", ["示範伴手禮"], (300, 600), (1, 2)),
    ]},
    {"label": "零食夜貓", "areas": {"新竹市東區": 6, "新竹縣竹北市": 4}, "habits": [
        (2, "示範超商", ["示範洋芋片", "示範巧克力", "示範布丁"], (30, 90), (12, 16)),
        (1, "示範超商", ["示範奶茶", "示範可樂"], (25, 60), (8, 12)),
        (0, "示範超商", ["示範鮪魚飯糰", "示範肉鬆飯糰"], (35, 80), (6, 9)),
        (8, "示範超商", ["示範衛生紙"], (50, 120), (1, 2)),
    ]},
    {"label": "家庭採買", "areas": {"桃園市中壢區": 7, "新北市板橋區": 3}, "habits": [
        (8, "示範量販", ["示範洗衣精", "示範衛生紙箱", "示範洗髮精"], (400, 1200), (4, 6)),
        (3, "示範量販", ["示範豬肉片", "示範雞肉分裝包", "示範蔬菜組合"], (500, 1200), (4, 6)),
        (2, "示範量販", ["示範家庭號餅乾"], (150, 300), (2, 3)),
        (0, "示範水餃館", ["示範韭菜豬肉水餃", "示範蔬菜水餃"], (150, 300), (3, 4)),
        (5, "示範洗衣坊", ["示範衣物清潔服務"], (150, 300), (1, 2)),
    ]},
]


def build_personas(per_type=5, seed=SEED):
    rng = random.Random(seed)
    people = []
    for kind in TYPES:
        areas, weights = zip(*kind["areas"].items())
        for member in range(per_type):
            flavor = "meat" if member in kind.get("meat_members", ()) else "veg"
            code, rows = f"P{len(people) + 1:02}", []
            for year, month, days in MONTHS:
                for category, merchant, items, (low, high), (fewest, most) in kind["habits"]:
                    names = items[flavor] if isinstance(items, dict) else items
                    for _ in range(rng.randint(fewest, most)):
                        rows.append({
                            "day": rng.randint(1, days), "invoice": f"{code}-{year}-{month:02}-{len(rows) + 1:03}",
                            "merchant": merchant, "name": rng.choice(names), "quantity": 1,
                            "amount": rng.randint(low, high), "category": category, "provisional": False,
                            "district": rng.choices(areas, weights)[0],
                        })
            people.append({"name": f"{kind['label']} {LETTERS[member]}", "type": kind["label"], "rows": rows})
    return people
