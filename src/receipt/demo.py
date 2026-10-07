"""Deterministic fictional purchases; never reads or transforms private records."""
import calendar


def build_demo(catalog):
    products = [name for name, value in catalog.items() if name not in ("示範餐盒折扣", "示範隨餐贈品")]
    prices = [125, 65, 85, 230, 90, 180, 45, 2100, 160, 780, 75]
    shops = ["示範餐坊", "示範茶屋", "示範烘焙店", "示範蔬果舖", "示範運動館", "示範洗衣坊", "示範客運", "示範旅宿", "示範生活館", "示範數位店", "示範選物店"]
    # Fictional shops placed in real districts; no street address is ever generated.
    districts = ["高雄市苓雅區", "高雄市苓雅區", "高雄市新興區", "高雄市苓雅區", "高雄市前鎮區", "高雄市苓雅區",
                 "高雄市新興區", "屏東縣恆春鎮", "高雄市新興區", "高雄市前鎮區", "高雄市新興區"]
    months = {}
    for month in (3, 4):
        key = f"2026-{month:02}"
        days = calendar.monthrange(2026, month)[1]
        counts = [13, 9, 5, 4, 4, 2, 5, 1, 3, 1, 1] if month == 3 else [11, 12, 4, 5, 6, 1, 7, 1, 2, 1, 1]
        rows = []
        for index, name in enumerate(products):
            for visit in range(counts[index]):
                rows.append({
                    "day": (index * 3 + visit * 5 + month) % days + 1,
                    "invoice": f"DEMO-{key}-{len(rows) + 1:03}",
                    "merchant": shops[index], "district": districts[index], "name": name, "quantity": 1,
                    "amount": prices[index] + (15 if month == 4 and index == 0 else 0),
                    **catalog[name],
                })
        first = rows[0]
        for name, amount in (("示範餐盒折扣", -25), ("示範隨餐贈品", 0)):
            rows.append({**first, "name": name, "amount": amount, **catalog[name]})
        months[key] = {"year": 2026, "monthNumber": month, "month": f"2026 年 {month} 月",
                       "days": days, "source": f"虛構示範資料（{month} 月）",
                       "rows": sorted(rows, key=lambda row: row["day"])}
    return months
