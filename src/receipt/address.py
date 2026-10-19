"""Reduce a seller address to its city and district, never keeping street details."""
import re

MUNICIPALITIES = ("臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹市", "嘉義市")
COUNTIES = ("新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣",
            "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣")
# County-administered cities sometimes appear without their county.
COUNTY_CITIES = {
    "竹北市": "新竹縣", "苗栗市": "苗栗縣", "頭份市": "苗栗縣", "彰化市": "彰化縣", "員林市": "彰化縣",
    "南投市": "南投縣", "斗六市": "雲林縣", "太保市": "嘉義縣", "朴子市": "嘉義縣", "屏東市": "屏東縣",
    "宜蘭市": "宜蘭縣", "花蓮市": "花蓮縣", "臺東市": "臺東縣", "馬公市": "澎湖縣",
}


def normalize_place(text):
    """Drop all spacing and write 台 as 臺, so place and brand names compare equal."""
    return re.sub(r"\s+", "", text).replace("台", "臺")


def parse_district(address):
    """Return city plus district, such as 高雄市苓雅區, or None when it cannot be read."""
    if not address:
        return None
    text = re.sub(r"^(臺灣省|臺灣)", "", re.sub(r"^\d+", "", normalize_place(address)))
    for city in MUNICIPALITIES + COUNTIES:
        if text.startswith(city):
            ending = "區" if city in MUNICIPALITIES else "[鄉鎮市]"
            match = re.match(r"\D{1,3}?" + ending, text[len(city):])
            return city + match.group() if match else None
    for town, county in COUNTY_CITIES.items():
        if text.startswith(town):
            return county + town
    return None
