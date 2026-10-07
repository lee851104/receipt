"""Deterministic fictional people to compare against; every shop, item and person here is made up."""
import random

from .signals import calendar_days

SEED = 20261007
MONTHS = ((2026, 3, 31), (2026, 4, 30))
PERIOD = tuple((year, month) for year, month, _ in MONTHS)
LETTERS = "ABCDE"
AWAY = ["屏東縣恆春鎮", "宜蘭縣宜蘭市", "屏東縣東港鎮"]

# A habit buys one item per visit. "merchant" may be a list paired one-to-one with "names".
# "days" is workday, offday, friday, long_weekend or any; "members" picks who in the type has the habit;
# "away" places the visits outside the person's own areas.
TYPES = [
    {"label": "省錢上班族", "areas": {"高雄市前鎮區": 6, "高雄市苓雅區": 4}, "habits": [
        {"category": 0, "merchant": "示範超商", "names": ["示範即期雞腿便當", "示範即期排骨便當", "示範即期咖哩飯"],
         "amount": (59, 79), "visits": (14, 18), "days": "workday"},
        {"category": 0, "merchant": "示範超商", "names": ["示範即期御飯糰"], "amount": (25, 35), "visits": (4, 6), "days": "offday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範無糖綠茶", "示範無糖烏龍茶"], "amount": (20, 30), "visits": (10, 14),
         "days": "workday"},
        {"category": 8, "merchant": "示範量販", "names": ["示範衛生紙箱", "示範洗衣精家庭號", "示範牙膏量販包"], "amount": (300, 600),
         "visits": (2, 3), "days": "offday", "members": (0, 1, 2)},
        {"category": 8, "merchant": "示範超商", "names": ["示範衛生紙", "示範牙膏"], "amount": (45, 90), "visits": (3, 4),
         "members": (3, 4)},
    ]},
    {"label": "忙碌工程師", "areas": {"新竹市東區": 6, "新竹縣竹北市": 4}, "habits": [
        {"category": 0, "merchant": "示範超商", "names": ["示範鮪魚飯糰", "示範肉鬆飯糰", "示範火腿三明治"], "amount": (35, 60),
         "visits": (14, 18), "days": "workday"},
        {"category": 0, "merchant": "示範超商", "names": ["示範微波義大利麵", "示範微波炒飯"], "amount": (79, 99), "visits": (6, 9),
         "days": "workday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範半糖拿鐵", "示範可樂"], "amount": (35, 65), "visits": (12, 16),
         "days": "workday"},
        {"category": 8, "merchant": "示範超商", "names": ["示範衛生紙", "示範牙刷", "示範洗面乳"], "amount": (39, 120), "visits": (3, 5)},
        {"category": 9, "merchant": "示範數位店", "names": ["示範機械鍵盤", "示範耳機", "示範傳輸線", "示範行動電源"],
         "amount": (300, 2500), "visits": (3, 4), "days": "offday"},
        {"category": 0, "merchant": "示範速食店", "names": ["示範雞排堡", "示範牛肉堡"], "amount": (120, 200), "visits": (3, 5),
         "days": "offday"},
        {"category": 1, "merchant": "示範居酒屋", "names": ["示範生啤酒"], "amount": (120, 180), "visits": (3, 4), "days": "friday",
         "members": (3, 4)},
    ]},
    {"label": "咖啡上班族", "areas": {"臺北市信義區": 6, "臺北市內湖區": 4}, "habits": [
        {"category": 1, "merchant": "示範精品咖啡", "names": ["示範冰美式", "示範熱美式"], "amount": (120, 160), "visits": (12, 16),
         "days": "workday", "members": (0, 1, 2)},
        {"category": 1, "merchant": "示範精品咖啡", "names": ["示範半糖拿鐵", "示範半糖焦糖拿鐵"], "amount": (130, 170),
         "visits": (12, 16), "days": "workday", "members": (3, 4)},
        {"category": 0, "merchant": ["示範簡餐店", "示範定食屋", "示範燴飯館"], "names": ["示範雞腿簡餐", "示範鮭魚定食", "示範牛肉燴飯"],
         "amount": (160, 260), "visits": (12, 15), "days": "workday"},
        {"category": 0, "merchant": "示範早午餐", "names": ["示範班尼迪克蛋", "示範鬆餅早午餐"], "amount": (280, 380), "visits": (3, 4),
         "days": "offday"},
        {"category": 2, "merchant": "示範精品咖啡", "names": ["示範可頌"], "amount": (70, 90), "visits": (3, 5), "days": "workday"},
    ]},
    {"label": "手搖學生", "areas": {"高雄市苓雅區": 6, "高雄市新興區": 4}, "habits": [
        {"category": 1, "merchant": ["示範茶屋", "示範果茶舖", "示範奶茶茶飲", "示範青茶坊"],
         "names": ["示範珍珠奶茶", "示範百香果茶", "示範黑糖珍珠鮮奶", "示範冬瓜青茶"], "amount": (45, 75), "visits": (12, 16),
         "members": (0, 1, 2)},
        {"category": 1, "merchant": ["示範茶屋", "示範果茶舖", "示範奶茶茶飲", "示範青茶坊"],
         "names": ["示範無糖綠茶", "示範無糖四季春", "示範無糖烏龍", "示範無糖青茶"], "amount": (35, 50), "visits": (12, 16),
         "members": (3, 4)},
        {"category": 2, "merchant": ["示範甜點店", "示範烘焙店", "示範豆花店"], "names": ["示範焦糖布丁", "示範肉桂捲", "示範花生豆花"],
         "amount": (50, 110), "visits": (5, 8)},
        {"category": 0, "merchant": ["示範餐坊", "示範麵館", "示範小吃店", "示範咖哩屋", "示範拉麵店", "示範越南小館", "示範韓式小館", "示範鬆餅屋"],
         "names": ["示範蔬食餐盒", "示範牛肉麵", "示範滷肉飯", "示範咖哩飯", "示範豚骨拉麵", "示範越南河粉", "示範石鍋拌飯", "示範鬆餅套餐"],
         "amount": (85, 140), "visits": (12, 16)},
        {"category": 5, "merchant": ["示範影城", "示範KTV", "示範桌遊店", "示範密室"],
         "names": ["示範電影票", "示範歡唱時段", "示範桌遊時段", "示範密室逃脫"], "amount": (250, 400), "visits": (2, 4), "days": "offday"},
        {"category": 6, "merchant": "示範客運", "names": ["示範客運票"], "amount": (40, 60), "visits": (5, 7), "days": "workday"},
        {"category": 4, "merchant": "示範運動館", "names": ["示範體適能體驗票"], "amount": (80, 100), "visits": (2, 3)},
        {"category": 8, "merchant": "示範文具店", "names": ["示範手帳", "示範筆記本"], "amount": (60, 120), "visits": (1, 3)},
    ]},
    {"label": "健身族", "areas": {"高雄市前鎮區": 5, "高雄市左營區": 5}, "habits": [
        {"category": 4, "merchant": "示範運動館", "names": ["示範重訓課", "示範健身入場"], "amount": (150, 300), "visits": (8, 10)},
        {"category": 4, "merchant": "示範運動館", "names": ["示範乳清蛋白粉"], "amount": (900, 1200), "visits": (1, 1)},
        {"category": 1, "merchant": "示範超商", "names": ["示範無糖豆漿", "示範無糖綠茶"], "amount": (25, 40), "visits": (8, 10)},
        {"category": 3, "merchant": "示範超市", "names": ["示範雞胸肉", "示範地瓜", "示範花椰菜", "示範雞蛋"], "amount": (80, 200),
         "visits": (6, 8), "days": "offday"},
        {"category": 0, "merchant": "示範餐坊", "names": ["示範雞肉餐盒", "示範舒肥雞沙拉"], "amount": (120, 160), "visits": (8, 10),
         "days": "workday"},
        {"category": 6, "merchant": "示範加油站", "names": ["示範95無鉛汽油"], "amount": (300, 600), "visits": (3, 4), "members": (3, 4)},
        {"category": 6, "merchant": "示範停車場", "names": ["示範停車費"], "amount": (40, 80), "visits": (4, 6), "members": (3, 4)},
    ]},
    {"label": "家庭下廚", "areas": {"桃園市中壢區": 7, "新北市板橋區": 3}, "habits": [
        {"category": 3, "merchant": "示範量販", "names": ["示範豬肉片", "示範雞腿肉", "示範高麗菜", "示範洋蔥", "示範雞蛋"],
         "amount": (150, 400), "visits": (8, 10), "days": "offday"},
        {"category": 3, "merchant": "示範量販", "names": ["示範醬油", "示範白米"], "amount": (90, 300), "visits": (2, 3), "days": "offday"},
        {"category": 8, "merchant": "示範量販", "names": ["示範衛生紙箱", "示範洗衣精家庭號", "示範洗碗精3入"], "amount": (300, 900),
         "visits": (3, 4), "days": "offday"},
        {"category": 6, "merchant": "示範加油站", "names": ["示範95無鉛汽油"], "amount": (800, 1500), "visits": (3, 4)},
        {"category": 0, "merchant": "示範水餃館", "names": ["示範韭菜豬肉水餃"], "amount": (150, 300), "visits": (2, 3)},
        {"category": 1, "merchant": "示範超商", "names": ["示範鮮奶"], "amount": (50, 90), "visits": (3, 5)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範犬用飼料", "示範狗零食"], "amount": (300, 900), "visits": (2, 3),
         "members": (0, 1, 2)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範貓飼料", "示範貓砂"], "amount": (250, 800), "visits": (2, 3),
         "members": (3, 4)},
    ]},
    {"label": "連假旅人", "areas": {"臺北市內湖區": 6, "新北市板橋區": 4}, "habits": [
        {"category": 7, "merchant": "示範旅宿", "names": ["示範旅店雙人房"], "amount": (1800, 3200), "visits": (2, 3),
         "days": "long_weekend", "away": AWAY, "members": (0, 1, 2)},
        {"category": 6, "merchant": "示範高鐵", "names": ["示範高鐵車票"], "amount": (700, 1500), "visits": (2, 2),
         "days": "long_weekend", "members": (0, 1, 2)},
        {"category": 0, "merchant": "示範海港餐廳", "names": ["示範海鮮套餐", "示範燒肉套餐"], "amount": (450, 900), "visits": (3, 4),
         "days": "long_weekend", "away": AWAY, "members": (0, 1, 2)},
        {"category": 7, "merchant": "示範旅宿", "names": ["示範旅店雙人房"], "amount": (1800, 3200), "visits": (1, 2),
         "days": "workday", "away": AWAY, "members": (3, 4)},
        {"category": 6, "merchant": "示範高鐵", "names": ["示範高鐵車票"], "amount": (700, 1500), "visits": (1, 1),
         "days": "workday", "members": (3, 4)},
        {"category": 0, "merchant": "示範海港餐廳", "names": ["示範海鮮套餐", "示範燒肉套餐"], "amount": (450, 900), "visits": (2, 3),
         "days": "workday", "away": AWAY, "members": (3, 4)},
        {"category": 0, "merchant": "示範便當店", "names": ["示範雞腿便當", "示範排骨便當"], "amount": (100, 140), "visits": (10, 13),
         "days": "workday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範礦泉水", "示範無糖綠茶"], "amount": (20, 40), "visits": (4, 6)},
        {"category": 5, "merchant": "示範遊樂園", "names": ["示範遊樂園門票"], "amount": (600, 900), "visits": (1, 1), "days": "offday"},
    ]},
    {"label": "質感貓奴", "areas": {"臺北市信義區": 5, "臺北市內湖區": 5}, "habits": [
        {"category": 8, "merchant": "示範選物店", "names": ["示範香氛蠟燭", "示範擴香瓶", "示範陶瓷杯"], "amount": (300, 800),
         "visits": (2, 3), "days": "offday"},
        {"category": 8, "merchant": "示範文具店", "names": ["示範手帳", "示範鋼筆", "示範紙膠帶貼紙"], "amount": (120, 400),
         "visits": (2, 3)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範貓飼料", "示範貓砂", "示範貓罐頭"], "amount": (200, 700), "visits": (3, 4)},
        {"category": 1, "merchant": "示範咖啡", "names": ["示範燕麥拿鐵", "示範手沖咖啡"], "amount": (110, 160), "visits": (6, 9)},
        {"category": 1, "merchant": "示範餐酒館", "names": ["示範精釀啤酒", "示範調酒"], "amount": (200, 350), "visits": (3, 4),
         "days": "offday", "members": (0, 1, 2)},
        {"category": 0, "merchant": ["示範餐坊", "示範義式餐館"], "names": ["示範青醬燉飯", "示範番茄義大利麵"], "amount": (220, 320),
         "visits": (8, 10)},
    ]},
]
FRIENDS = (("小安", "咖啡上班族", 0), ("小宇", "咖啡上班族", 3), ("小林", "質感貓奴", 0))


def pick_days(rule, days, off, long_weekend):
    if rule == "workday":
        return [day for day in days if day not in off]
    if rule == "offday":
        return [day for day in days if day in off]
    if rule == "friday":
        return [day for day in days if day.weekday() == 4 and day not in off]
    if rule == "long_weekend":
        return [day for day in days if day in long_weekend]
    return days


def build_person(name, kind, member, code, rng, calendar):
    days, off, long_weekend = calendar_days(PERIOD, calendar)
    areas, weights = zip(*kind["areas"].items())
    rows = []
    for year, month in PERIOD:
        month_days = [day for day in days if day.month == month]
        for habit in kind["habits"]:
            if member not in habit.get("members", range(len(LETTERS))):
                continue
            pool = pick_days(habit.get("days", "any"), month_days, off, long_weekend)
            for _ in range(rng.randint(*habit["visits"]) if pool else 0):
                when = rng.choice(pool)
                pick = rng.randrange(len(habit["names"]))
                merchant = habit["merchant"][pick] if isinstance(habit["merchant"], list) else habit["merchant"]
                rows.append({
                    "date": when, "day": when.day, "invoice": f"{code}-{year}-{month:02}-{len(rows) + 1:03}",
                    "merchant": merchant,
                    "district": rng.choice(habit["away"]) if "away" in habit else rng.choices(areas, weights)[0],
                    "name": habit["names"][pick], "quantity": 1, "amount": rng.randint(*habit["amount"]),
                    "category": habit["category"], "provisional": False,
                })
    return {"name": name, "type": kind["label"], "rows": rows}


def build_personas(calendar, per_type=5, seed=SEED):
    rng = random.Random(seed)
    people = []
    for kind in TYPES:
        for member in range(per_type):
            people.append(build_person(f"{kind['label']} {LETTERS[member]}", kind, member, f"P{len(people) + 1:02}", rng, calendar))
    return people


def build_friends(calendar, seed=SEED):
    """小安、小宇 and 小林 for the friend comparison, made the same way as the fictional population."""
    kinds = {kind["label"]: kind for kind in TYPES}
    return [build_person(name, kinds[label], member, f"F{index + 1}", random.Random(seed + index + 1), calendar)
            for index, (name, label, member) in enumerate(FRIENDS)]
