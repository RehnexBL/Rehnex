"""
update_stats.py
----------------
Pulls current store stats from the BrickLink API and writes them into
site-config.json, WITHOUT touching the "announcement" section (so your
manually-toggled sale banner isn't overwritten by automation).

This is a STARTER SCRIPT — plug in your existing OAuth 1.0a request logic
(the same auth you already use in fill_pickabrick.py / your price lookup
tool). The endpoint paths below are correct as of BrickLink API v1, but
double check them against your working scripts / the current API docs
before trusting the output, since a couple of these (esp. feedback/rating)
may need small adjustments depending on what your account has access to.

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


def get_unique_parts_count():
    """Count of unique inventory lots currently listed in your store."""
    resp = session.get(f"{BASE_URL}/inventories", params={"status": "Y"})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return len(data)


def get_orders_shipped_count():
    """
    Count of completed/shipped orders. Note: BrickLink's /orders endpoint
    typically only returns a rolling window of recent orders, not full
    historical count — if that's the case for your account, consider
    keeping a running total in site-config.json and adding to it, rather
    than recalculating from scratch each time.
    """
    resp = session.get(f"{BASE_URL}/orders", params={"direction": "out", "status": "Completed"})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return len(data)


def get_feedback_stats():
    """
    Feedback score / positive rating. Verify this endpoint against your
    account — BrickLink's feedback resource may be scoped differently
    (e.g. /feedback vs. a member ratings summary). If it doesn't return
    what you expect, this is the one to hand-edit less frequently instead
    of automating, since it changes slowly anyway.
    """
    resp = session.get(f"{BASE_URL}/feedback", params={"direction": "in"})
    resp.raise_for_status()
    feedback_list = resp.json().get("data", [])
    positive = sum(1 for f in feedback_list if f.get("rating_of_bs") == "Positive")
    total = len(feedback_list)
    positive_pct = round((positive / total) * 100) if total else 0
    return total, positive_pct


def main():
    config_path = os.path.join(os.path.dirname(__file__), "site-config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    unique_parts = get_unique_parts_count()
    orders_shipped = get_orders_shipped_count()
    feedback_score, positive_rating = get_feedback_stats()

    config["stats"] = {
        "ordersShipped": orders_shipped,
        "uniqueParts": unique_parts,
        "feedbackScore": feedback_score,
        "positiveRating": positive_rating,
        "lastUpdated": date.today().isoformat(),
    }
    # "announcement" section is left untouched on purpose.

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Updated stats: {config['stats']}")


if __name__ == "__main__":
    main()
