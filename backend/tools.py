import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "listings.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    return conn


def search_listings(
    listing_type: Optional[str] = None,
    emirate: Optional[str] = None,
    area: Optional[str] = None,
    bedrooms: Optional[int] = None,
    max_price_aed: Optional[int] = None,
    furnished: Optional[bool] = None,
    near_metro: Optional[bool] = None,
    parking: Optional[bool] = None,
) -> list[dict]:
    """Search the property listings database. Returns up to 5 cheapest matches.

    Args:
        listing_type: Either "rent" or "sale".
        emirate: One of "Sharjah", "Dubai", "Ajman", "Abu Dhabi".
        area: Neighbourhood name, for example "Al Nahda" or "Dubai Marina".
        bedrooms: Number of bedrooms. Use 0 for a studio.
        max_price_aed: Maximum price in AED. For rent this is per year.
        furnished: True for furnished only, False for unfurnished only.
        near_metro: True for listings within walking distance of Dubai Metro.
        parking: True for listings that include parking.
    """
    sql = "SELECT * FROM listings WHERE 1=1"
    params = []

    if listing_type:
        sql += " AND listing_type = ?"
        params.append(listing_type.lower())
    if emirate:
        sql += " AND LOWER(emirate) = ?"
        params.append(emirate.lower())
    if area:
        sql += " AND LOWER(area) LIKE ?"
        params.append(f"%{area.lower()}%")
    if bedrooms is not None:
        sql += " AND bedrooms = ?"
        params.append(bedrooms)
    if max_price_aed is not None:
        sql += " AND price_aed <= ?"
        params.append(max_price_aed)
    if furnished is not None:
        sql += " AND furnished = ?"
        params.append(1 if furnished else 0)
    if near_metro is not None:
        sql += " AND near_metro = ?"
        params.append(1 if near_metro else 0)
    if parking is not None:
        sql += " AND parking = ?"
        params.append(1 if parking else 0)

    sql += " ORDER BY price_aed ASC LIMIT 5"

    conn = _connect()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def compare_listings(listing_ids: list[int]) -> list[dict]:
    """Compare several listings side by side, including price per square foot.

    Args:
        listing_ids: The ID numbers of the listings to compare (2 to 4 IDs).
    """
    conn = _connect()
    results = []
    for listing_id in listing_ids[:4]:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()
        if row:
            item = dict(row)
            item["price_per_sqft_aed"] = round(item["price_aed"] / item["size_sqft"])
            results.append(item)
    conn.close()
    return results


# This part only runs when we run this file directly (to test without AI)
if __name__ == "__main__":
    print("Test: 2-bedroom rentals in Sharjah\n")
    for r in search_listings(listing_type="rent", emirate="Sharjah", bedrooms=2):
        print(r["id"], r["title"], r["price_aed"])