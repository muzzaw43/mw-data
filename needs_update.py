#!/usr/bin/env python3
"""Decide whether a scheduled run should rebuild the card database.

Rebuild when it is Monday (weekly run), or when a set released in the last WINDOW_DAYS days
still has cards that are missing from the live mtg_cards_slim.json (new set not fully registered yet).
Prints "yes <reason>" or "no <reason>" and exits 0.  Any error -> "yes" (fail towards updating).
"""
import datetime
import json
import sys
import urllib.request

WINDOW_DAYS = 45
BASE = "https://mtgjson.com/api/v5/"
UA = {"User-Agent": "mw-data-updater (github.com/muzzaw43/mw-data)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if today.weekday() == 0:
        print("yes weekly Monday run")
        return
    try:
        live = json.load(open("mtg_cards_slim.json", encoding="utf-8"))
        sets = get(BASE + "SetList.json")["data"]
        recent = [s for s in sets
                  if s.get("type") in ("expansion", "core", "commander", "draft_innovation", "masters", "funny", "eternal", "starter", "box")
                  and today - datetime.timedelta(days=WINDOW_DAYS) <= datetime.date.fromisoformat(s["releaseDate"]) <= today]
        for s in sorted(recent, key=lambda x: x["releaseDate"]):
            cards = get(BASE + s["code"] + ".json")["data"]["cards"]
            missing = sorted({c["name"] for c in cards} - set(live))
            # alchemy-style "A-" names and tokens are not in the slim file by design
            missing = [m for m in missing if not m.startswith("A-")]
            if missing:
                print(f"yes {s['code']} ({s['name']}, released {s['releaseDate']}) has {len(missing)} cards not in the live file, e.g. {missing[:3]}")
                return
        print(f"no {len(recent)} recent sets, all registered")
    except Exception as e:  # noqa: BLE001
        print(f"yes could not check recent sets ({e})")


if __name__ == "__main__":
    main()
