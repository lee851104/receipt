"""Names shared by the category and attribute models, their fakes and the API."""

CATEGORY_COUNT = 10  # models answer 0-9; 10 (待確認) is decided later from the probability, never by a model
ATTRIBUTES = ("clearance", "sugar", "quick", "cooking", "kitchen", "sport_supply", "sport_gear", "car_care",
              "bulk", "home", "stationery", "fun", "pet_food", "pet_supply", "species", "alcohol")
FLAGS = ("food", "meal", "drink", "fresh", "daily", "tech", "sport")
FIELDS = ATTRIBUTES + FLAGS  # what describe_items() answers for one name; None means unknown, never False
