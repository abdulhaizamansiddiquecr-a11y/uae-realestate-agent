from pathlib import Path
import random
import sqlite3

random.seed(42)  # makes the data the same every time we run this

# emirate, area, rent (AED per sqft per year), sale price (AED per sqft), near Dubai Metro?
AREAS = [
    ("Sharjah", "Al Nahda", 40, 650, False),
    ("Sharjah", "Al Majaz", 50, 800, False),
    ("Sharjah", "Al Khan", 55, 900, False),
    ("Sharjah", "Muwaileh", 38, 600, False),
    ("Sharjah", "Aljada", 60, 1000, False),
    ("Dubai", "Jumeirah Village Circle", 65, 1100, False),
    ("Dubai", "Dubai Marina", 110, 1900, True),
    ("Dubai", "Business Bay", 100, 1700, True),
    ("Dubai", "Deira", 60, 950, True),
    ("Dubai", "Al Barsha", 70, 1150, True),
    ("Dubai", "Discovery Gardens", 55, 900, True),
    ("Dubai", "Downtown Dubai", 150, 2800, True),
    ("Ajman", "Al Rashidiya", 30, 500, False),
    ("Ajman", "Ajman Downtown", 35, 550, False),
    ("Abu Dhabi", "Al Reem Island", 85, 1500, False),
    ("Abu Dhabi", "Khalidiya", 75, 1300, False),
]

COASTAL = {"Al Khan", "Dubai Marina", "Al Reem Island", "Al Majaz"}

# bedrooms: (min sqft, max sqft)
SIZES = {0: (350, 520), 1: (600, 950), 2: (1000, 1500), 3: (1500, 2200)}

FEATURES = [
    "gym", "swimming pool", "balcony", "covered parking",
    "maid's room", "kids play area", "24/7 security",
    "central AC", "built-in wardrobes", "close to schools",
    "close to supermarkets", "quiet building",
]

conn = sqlite3.connect(Path(__file__).parent / "listings.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS listings")
cur.execute("""
CREATE TABLE listings (
    id INTEGER PRIMARY KEY,
    title TEXT,
    emirate TEXT,
    area TEXT,
    listing_type TEXT,      -- 'rent' or 'sale'
    bedrooms INTEGER,       -- 0 means studio
    bathrooms INTEGER,
    size_sqft INTEGER,
    price_aed INTEGER,      -- per year if rent, total price if sale
    furnished INTEGER,      -- 1 = yes, 0 = no
    parking INTEGER,        -- 1 = yes, 0 = no
    near_metro INTEGER,     -- 1 = near Dubai Metro, 0 = no
    description TEXT
)
""")

for i in range(1, 81):
    emirate, area, rent_rate, sale_rate, metro = random.choice(AREAS)
    beds = random.choice([0, 1, 1, 2, 2, 2, 3])
    size = random.randint(*SIZES[beds])
    listing_type = "sale" if random.random() < 0.25 else "rent"

    rate = sale_rate if listing_type == "sale" else rent_rate
    price = size * rate * random.uniform(0.85, 1.15)
    price = round(price, -4) if listing_type == "sale" else round(price, -3)

    baths = max(1, beds)
    furnished = random.choice([0, 1])
    parking = 1 if random.random() < 0.8 else 0

    kind = "Studio" if beds == 0 else f"{beds}-bedroom apartment"
    title = f"{kind} in {area}, {emirate}"

    features = random.sample(FEATURES, 3)
    if area in COASTAL:
        view = random.choice(["sea view", "city view"])
    else:
        view = random.choice(["city view", "pool view", "garden view"])
    features.append(view)
    if metro:
        features.append("walking distance to Dubai Metro")

    description = (
        f"{title}. {size} sqft, {'furnished' if furnished else 'unfurnished'}. "
        f"Features: {', '.join(features)}."
    )

    cur.execute(
        "INSERT INTO listings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, title, emirate, area, listing_type, beds, baths, size,
         int(price), furnished, parking, int(metro), description),
    )

conn.commit()

# Show a quick summary so we know it worked
count = cur.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
print(f"Created {count} listings.\n")
print("Here are 3 examples:\n")
for row in cur.execute("SELECT title, listing_type, price_aed, description FROM listings LIMIT 3"):
    print(row)
    print()

conn.close()
