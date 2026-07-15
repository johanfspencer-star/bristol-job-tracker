"""
Bristol / South West job market snapshot
-----------------------------------------
Pulls current vacancy counts, category breakdown, salary distribution and
top hiring companies from the Adzuna API, and appends the result to a
running history so the dashboard can plot trends over time.

Requires two environment variables (get free keys at https://developer.adzuna.com/):
    ADZUNA_APP_ID
    ADZUNA_APP_KEY

Usage:
    python3 fetch_data.py

No third-party packages required, everything here is Python stdlib on purpose
so it runs on a bare GitHub Actions runner with zero pip install step.

Note: endpoint and parameter names below are taken from Adzuna's public docs
(developer.adzuna.com) and their published API overview. I haven't been able
to test live calls while writing this (sandboxed, no network access to their
API), so the first run is worth watching closely, if a field comes back
named differently than expected, check the response JSON printed in the
Actions log and adjust the relevant `.get(...)` call below.
"""

import os
import json
import csv
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_APP_KEY")
COUNTRY = "gb"
BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}"

# Adzuna's `where` param does free-text location matching with a built-in
# radius. Bristol on its own catches the city; South West England is queried
# separately so the dashboard can show "city" vs "wider region" side by side.
LOCATIONS = {
    "Bristol": "Bristol",
    "South West": "South West England",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def api_get(path, params):
    """Call the Adzuna API and return parsed JSON, or None on failure."""
    if not APP_ID or not APP_KEY:
        raise RuntimeError(
            "Missing ADZUNA_APP_ID / ADZUNA_APP_KEY environment variables. "
            "Get free keys at https://developer.adzuna.com/"
        )
    query = {"app_id": APP_ID, "app_key": APP_KEY}
    query.update(params)
    url = f"{BASE_URL}/{path}?{urllib.parse.urlencode(query)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        print(f"  ! HTTP {e.code} calling {path}: {body}")
    except Exception as e:
        print(f"  ! Error calling {path}: {e}")
    return None


def get_categories():
    data = api_get("categories", {})
    if not data:
        return []
    return [c["tag"] for c in data.get("results", [])]


def get_total_count(where):
    data = api_get("search/1", {"where": where, "results_per_page": 1})
    return data.get("count") if data else None


def get_category_counts(where, categories):
    counts = {}
    for cat in categories:
        data = api_get(
            "search/1", {"where": where, "category": cat, "results_per_page": 1}
        )
        counts[cat] = data.get("count", 0) if data else 0
        time.sleep(0.3)  # go easy on the free tier rate limit
    return counts


def get_salary_histogram(where):
    data = api_get("histogram", {"where": where})
    return data.get("histogram", {}) if data else {}


def get_top_companies(where):
    data = api_get("top_companies", {"where": where})
    return data.get("leaderboard", []) if data else []


def main():
    today = datetime.date.today().isoformat()
    print(f"Fetching Adzuna snapshot for {today}...")

    categories = get_categories()
    if not categories:
        print("Could not fetch category list, aborting.")
        return
    print(f"  Found {len(categories)} categories")

    snapshot = {"date": today, "locations": {}}

    for label, where in LOCATIONS.items():
        print(f"  Location: {label} ({where})")
        total = get_total_count(where)
        cat_counts = get_category_counts(where, categories)
        salary_hist = get_salary_histogram(where)
        top_companies = get_top_companies(where)

        snapshot["locations"][label] = {
            "where": where,
            "total_vacancies": total,
            "by_category": cat_counts,
            "salary_histogram": salary_hist,
            "top_companies": top_companies,
        }
        print(f"    total_vacancies = {total}")

    # Full snapshot for the day, kept for auditing / debugging
    snap_path = os.path.join(DATA_DIR, f"snapshot_{today}.json")
    with open(snap_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Overwritten each run, this is what the dashboard reads
    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Appended each run, this is what powers the trend line
    history_path = os.path.join(DATA_DIR, "history.csv")
    file_exists = os.path.exists(history_path)
    with open(history_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "location", "total_vacancies"])
        for label, loc_data in snapshot["locations"].items():
            writer.writerow([today, label, loc_data["total_vacancies"]])

    print("Done.")


if __name__ == "__main__":
    main()
