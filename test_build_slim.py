"""Self-test: turn the live slim file back into MTGJSON-style atomic cards, rebuild it, and require an exact match.
Also checks the legality rules on a few hand-made cards."""
import json
import sys

import build_slim as B


def to_atomic(slim):
    data = {}
    for name, faces in slim.items():
        out = []
        for f in faces:
            a = {k: v for k, v in f.items() if k not in ("commanderLegal", "colorIdentity", "colors", "keywords", "name")}
            a["name"] = name
            a["colorIdentity"] = [x for x in f.get("colorIdentity", "").split(", ") if x]
            a["colors"] = [x for x in f.get("colors", "").split(", ") if x]
            if f.get("keywords"):
                a["keywords"] = f["keywords"].split(", ")
            a["legalities"] = {"commander": "Legal" if f["commanderLegal"] else "Banned"}
            out.append(a)
        data[name] = out
    return {"meta": {"date": "test"}, "data": data}


def main(path):
    old = json.load(open(path, encoding="utf-8"))
    new = B.build(to_atomic(old))
    bad = [n for n in old if new.get(n) != old[n]]
    print(f"round trip: {len(old)} cards, {len(bad)} differ")
    for n in bad[:5]:
        print(" ", n, "\n   old", old[n], "\n   new", new.get(n))
    # legality rules
    card = lambda lg: {"data": {"X": [{"layout": "normal", "manaValue": 1, "type": "Instant", "legalities": lg}]}}
    cases = [({"commander": "Legal"}, True), ({"commander": "Banned"}, False), ({"commander": "Not Legal"}, False), ({}, False), ({"modern": "Legal"}, False)]
    for lg, want in cases:
        got = B.build(card(lg))["X"][0]["commanderLegal"]
        assert got == want, (lg, got, want)
    print("legality rules ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "mtg_cards_slim.json"))
