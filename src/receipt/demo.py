"""Deterministic fictional purchases; never reads or transforms private records."""
import calendar

# One slot per kind of purchase: (shop and item pairs, price, visits in March, visits in April, district).
# Visits rotate through the pairs, so a slot can span several shops and dishes.
SLOTS = [
    ([("示範餐坊", "示範蔬食餐盒"), ("示範燉飯屋", "示範番茄燉飯"), ("示範麵館", "示範香菇湯麵"),
      ("示範咖哩屋", "示範蔬菜咖哩"), ("示範越南小館", "示範越南河粉"), ("示範韓式小館", "示範石鍋拌飯")],
     125, 13, 11, "高雄市苓雅區"),
    ([("示範茶屋", "示範花果茶"), ("示範果茶舖", "示範百香果茶"), ("示範青茶坊", "示範半糖冬瓜青茶")], 65, 9, 12, "高雄市苓雅區"),
    ([("示範烘焙店", "示範燕麥餅"), ("示範甜點店", "示範焦糖布丁"), ("示範豆花店", "示範花生豆花")], 85, 5, 4, "高雄市新興區"),
    ([("示範蔬果舖", "示範綜合蔬菜箱"), ("示範傳統市場", "示範有機蔬菜")], 230, 4, 5, "高雄市苓雅區"),
    ([("示範運動館", "示範體適能體驗票")], 90, 4, 6, "高雄市前鎮區"),
    ([("示範洗衣坊", "示範衣物清潔服務")], 180, 2, 1, "高雄市苓雅區"),
    ([("示範客運", "示範市區接駁票")], 45, 5, 7, "高雄市新興區"),
    ([("示範旅宿", "示範旅店雙人房")], 2100, 1, 1, "屏東縣恆春鎮"),
    ([("示範生活館", "示範環保清潔劑")], 160, 3, 2, "高雄市新興區"),
    ([("示範數位店", "示範無線滑鼠")], 780, 1, 1, "高雄市前鎮區"),
    ([("示範選物店", "示範未分類商品")], 75, 1, 1, "高雄市新興區"),
]


def build_demo(catalog):
    months = {}
    for month in (3, 4):
        key = f"2026-{month:02}"
        days = calendar.monthrange(2026, month)[1]
        rows = []
        for index, (pairs, price, march, april, district) in enumerate(SLOTS):
            for visit in range(march if month == 3 else april):
                merchant, name = pairs[visit % len(pairs)]
                rows.append({
                    "day": (index * 3 + visit * 5 + month) % days + 1,
                    "invoice": f"DEMO-{key}-{len(rows) + 1:03}",
                    "merchant": merchant, "district": district, "name": name, "quantity": 1,
                    "amount": price + (15 if month == 4 and index == 0 else 0),
                    **catalog[name],
                })
        first = rows[0]
        for name, amount in (("示範餐盒折扣", -25), ("示範隨餐贈品", 0)):
            rows.append({**first, "name": name, "amount": amount, **catalog[name]})
        months[key] = {"year": 2026, "monthNumber": month, "month": f"2026 年 {month} 月",
                       "days": days, "source": f"虛構示範資料（{month} 月）",
                       "rows": sorted(rows, key=lambda row: row["day"])}
    return months
