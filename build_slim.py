#!/usr/bin/env python3
"""Rebuild mtg_cards_slim.json from MTGJSON AtomicCards (one entry per card, one legality per card).

Usage:
  python build_slim.py --out staging/mtg_cards_slim.json --summary staging/SUMMARY.md
  python build_slim.py --source AtomicCards.json.gz --existing mtg_cards_slim.json ...

Output format matches the existing file exactly: {"Card Name": [face, ...]}, compact JSON, no trailing newline.
"""
import argparse
import gzip
import io
import json
import os
import sys
import time
import urllib.request

SRC = "https://mtgjson.com/api/v5/AtomicCards.json.gz"
META = "https://mtgjson.com/api/v5/Meta.json"
UA = "mw-data-updater (github.com/muzzaw43/mw-data)"


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"could not download {url}: {last}")


def load_source(src):
    if src.startswith("http"):
        raw = fetch(src)
    else:
        with open(src, "rb") as f:
            raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def join(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v)


def slim_face(f, name):
    """One MTGJSON atomic face -> one slim face (same keys/order as the existing file)."""
    out = {"name": name}
    if f.get("faceName"):
        out["faceName"] = f["faceName"]
    if f.get("side"):
        out["side"] = f["side"]
    out["layout"] = f.get("layout", "normal")
    if f.get("manaCost"):
        out["manaCost"] = f["manaCost"]
    out["manaValue"] = float(f.get("manaValue", 0) or 0)
    if f.get("faceManaValue") is not None:
        out["faceManaValue"] = float(f["faceManaValue"])
    ci = ", ".join(sorted(f.get("colorIdentity") or []))
    if ci:
        out["colorIdentity"] = ci
    cs = ", ".join(f.get("colors") or [])
    if cs:
        out["colors"] = cs
    out["type"] = f.get("type", "")
    if f.get("text"):
        out["text"] = f["text"]
    for k in ("power", "toughness", "loyalty", "defense"):
        if f.get(k) not in (None, ""):
            out[k] = str(f[k])
    kw = join(f.get("keywords"))
    if kw:
        out["keywords"] = kw
    # Card-level Commander legality: only the status "Legal" counts (Banned / Not Legal / missing = not legal).
    out["commanderLegal"] = (f.get("legalities") or {}).get("commander") == "Legal"
    return out


def build(atomic):
    data = atomic["data"] if "data" in atomic else atomic
    out = {}
    for name in sorted(data):
        faces = data[name]
        out[name] = [slim_face(f, name) for f in faces]
    return out


def dump(d, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))


def is_legal(faces):
    return all(f.get("commanderLegal") is not False for f in faces)


def summary(new, old, meta, watch):
    L = ["# Card database update (staged, not live yet)", ""]
    if meta:
        L.append(f"Source: MTGJSON AtomicCards, build {meta.get('date', '?')} (version {meta.get('version', '?')}).")
    L.append(f"Cards in new file: **{len(new)}**" + (f" (live file has {len(old)})" if old is not None else ""))
    if old is not None:
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        L.append(f"Added: **{len(added)}**, removed: **{len(removed)}**")
        flagged_new = sum(1 for f in new.values() if not is_legal(f))
        flagged_old = sum(1 for f in old.values() if not is_legal(f))
        L.append(f"Flagged not Commander-legal: **{flagged_new}** (live file: {flagged_old})")
        common = [n for n in new if n in old]
        tf = sorted(n for n in common if is_legal(old[n]) and not is_legal(new[n]))
        ft = sorted(n for n in common if not is_legal(old[n]) and is_legal(new[n]))
        L.append(f"Legality changes: {len(ft)} now legal, {len(tf)} now not legal")
        text_changed = sorted(n for n in common if [f.get("text") for f in new[n]] != [f.get("text") for f in old[n]])
        L.append(f"Rules text changed on {len(text_changed)} existing cards")
        L += ["", "## Watch list"]
        for w in watch:
            L.append(f"- {w}: {'in new file' if w in new else 'NOT in new file'}; {'already in live file' if w in old else 'not in live file'}")
        L += ["", "## Added (first 80)"] + [f"- {n}" for n in added[:80]]
        L += ["", "## Removed (first 40)"] + [f"- {n}" for n in removed[:40]]
        L += ["", "## Now legal (first 60)"] + [f"- {n}" for n in ft[:60]]
        L += ["", "## Now NOT legal (first 60)"] + [f"- {n}" for n in tf[:60]]
        L += ["", "## Rules text changed (first 25)"] + [f"- {n}" for n in text_changed[:25]]
    else:
        L += ["", "## Watch list"] + [f"- {w}: {'in new file' if w in new else 'NOT in new file'}" for w in watch]
    return "\n".join(L) + "\n"


def sanity(new, old):
    problems = []
    if len(new) < 30000:
        problems.append(f"only {len(new)} cards (expected 30,000+)")
    for must in ("Sol Ring", "Lightning Bolt", "Black Lotus"):
        if must not in new:
            problems.append(f"missing {must}")
    if new.get("Sol Ring") and not is_legal(new["Sol Ring"]):
        problems.append("Sol Ring flagged not legal")
    if old is not None and not (0.9 * len(old) <= len(new) <= 1.2 * len(old)):
        problems.append(f"card count {len(new)} is far from the live file's {len(old)}")
    for n in ("Talisman of Progress", "Annul", "Dark Ritual"):
        pass
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=SRC)
    ap.add_argument("--out", default="staging/mtg_cards_slim.json")
    ap.add_argument("--summary", default="staging/SUMMARY.md")
    ap.add_argument("--existing", default="mtg_cards_slim.json")
    ap.add_argument("--watch", default="watch.txt")
    ap.add_argument("--force", action="store_true", help="write the output even if the sanity checks fail")
    a = ap.parse_args()

    meta = None
    if a.source.startswith("http"):
        try:
            meta = json.loads(fetch(META).decode("utf-8")).get("meta")
        except Exception as e:  # noqa: BLE001
            print("warning: could not read Meta.json:", e, file=sys.stderr)
    atomic = load_source(a.source)
    if meta is None and isinstance(atomic, dict) and "meta" in atomic:
        meta = atomic["meta"]
    new = build(atomic)
    old = None
    if a.existing and os.path.exists(a.existing):
        with open(a.existing, encoding="utf-8") as f:
            old = json.load(f)
    watch = []
    if a.watch and os.path.exists(a.watch):
        watch = [l.strip() for l in open(a.watch, encoding="utf-8") if l.strip() and not l.startswith("#")]
    problems = sanity(new, old)
    text = summary(new, old, meta, watch)
    if problems:
        text = "# BUILD NOT STAGED\n\n" + "\n".join(f"- {p}" for p in problems) + "\n\n" + text
    os.makedirs(os.path.dirname(os.path.abspath(a.summary)), exist_ok=True)
    with open(a.summary, "w", encoding="utf-8") as f:
        f.write(text)
    if problems and not a.force:
        print("sanity checks failed:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    dump(new, a.out)
    print(f"wrote {a.out}: {len(new)} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
