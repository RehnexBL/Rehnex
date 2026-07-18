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
    Returns (unique_lots, total_items).
    - unique_lots: number of inventory listings ("lots") currently live.
    - total_items: total piece count across all lots (sum of quantity).
    """
    resp = session.get(f"{BASE_URL}/inventories", params={"status": "Y"})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    unique_lots = len(data)
    total_items = sum(lot.get("quantity", 0) for lot in data)
    return unique_lots, total_items


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

    unique_lots, total_items = get_inventory_stats()
    feedback_received = get_feedback_received_count()

    config["stats"] = {
        "uniqueLots": unique_lots,
        "totalItems": total_items,
        "feedbackReceived": feedback_received,
        "lastUpdated": date.today().isoformat(),
    }
    # "announcement" section is left untouched on purpose.

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Updated stats: {config['stats']}")


if __name__ == "__main__":
    main()
