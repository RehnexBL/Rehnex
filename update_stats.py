"""
update_stats.py
----------------
Pulls current store stats from the BrickLink API and writes them into
site-config.json, WITHOUT touching the "announcement" section (so your
manually-toggled sale banner isn't overwritten by automation).

Run this daily via a GitHub Action (see update-stats.yml).
"""

import json
import os
from datetime import date
from requests_oauthlib import OAuth1Session

# ---- Auth: pull from environment variables (set as GitHub Secrets) ----
CONSUMER_KEY = os.environ["BL_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["BL_CONSUMER_SECRET"]
TOKEN_VALUE = os.environ["BL_TOKEN_VALUE"]
TOKEN_SECRET = os.environ["BL_TOKEN_SECRET"]
STORE_USERNAME = os.environ["BL_USERNAME"]  # your BrickLink username

BASE_URL = "https://api.bricklink.com/api/store/v1"

session = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=TOKEN_VALUE,
    resource_owner_secret=TOKEN_SECRET,
)


def get_inventory_stats():
    """
    Returns (unique_lots, total_items, color_ids).
    - unique_lots: number of inventory listings ("lots") currently live.
    - total_items: total piece count across all lots (sum of quantity).
    - color_ids: sorted list of distinct BrickLink color IDs actually
      used across your current inventory (parts often have no color,
      e.g. sets/minifigs — those are skipped).
    """
    resp = session.get(f"{BASE_URL}/inventories", params={"status": "Y"})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    unique_lots = len(data)
    total_items = sum(lot.get("quantity", 0) for lot in data)
    color_ids = sorted({
        lot.get("color_id") for lot in data
        if lot.get("color_id") not in (None, 0)
    })
    return unique_lots, total_items, color_ids


def get_color_names(color_ids):
    """
    Resolves color IDs to their real names using BrickLink's own /colors
    catalog endpoint (public reference data, not inventory-specific) —
    this keeps the color dropdown on the splash page accurate even as
    BrickLink adds new colors, instead of relying on a hand-typed list.
    """
    resp = session.get(f"{BASE_URL}/colors")
    resp.raise_for_status()
    all_colors = resp.json().get("data", [])
    name_lookup = {c["color_id"]: c["color_name"] for c in all_colors}
    return [
        {"id": cid, "name": name_lookup.get(cid, f"Color {cid}")}
        for cid in color_ids
    ]


def get_feedback_received_count():
    """Total number of feedback entries received (not a score/rating)."""
    resp = session.get(f"{BASE_URL}/feedback", params={"direction": "in"})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return len(data)


def main():
    config_path = os.path.join(os.path.dirname(__file__), "site-config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    unique_lots, total_items, color_ids = get_inventory_stats()
    feedback_received = get_feedback_received_count()
    colors_in_stock = get_color_names(color_ids)

    config["stats"] = {
        "uniqueLots": unique_lots,
        "totalItems": total_items,
        "feedbackReceived": feedback_received,
        "lastUpdated": date.today().isoformat(),
    }
    config["colorsInStock"] = colors_in_stock
    # "announcement" section is left untouched on purpose.

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Updated stats: {config['stats']}")
    print(f"Colors in stock: {len(colors_in_stock)}")


if __name__ == "__main__":
    main()
