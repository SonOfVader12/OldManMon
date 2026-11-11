#!/usr/bin/env python3
"""
scan_recipes.py  (step 1 of 2)

Reads a mod jar (or extracted folder), finds crafting-table recipes for one
namespace, sorts each recipe's output item into a category by keyword, and
writes a CSV:  item,category

Items no keyword matched get an EMPTY category. Open the CSV in any editor,
fix categories or fill in blanks, then feed it to build_pack.py. Rows with an
empty category are ignored by build_pack.py.

USAGE
    python3 scan_recipes.py --jar cobblemon-fabric-1.6.1.jar --namespace cobblemon
    python3 scan_recipes.py --jar mod.jar --namespace mymod --out mymod.csv --rules rules.json

The CSV file name (without .csv) becomes the mod id in step 2, so name it
what you want the tags/tab to be called.
"""
import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path

# group -> substrings matched against the item path (text after ':').
# First matching group wins. A trailing "$" means "must END with this".
DEFAULT_RULES = {
    "pokeballs": [
        "poke_ball", "great_ball", "ultra_ball", "master_ball", "premier_ball",
        "heal_ball", "net_ball", "dive_ball", "nest_ball", "repeat_ball",
        "timer_ball", "luxury_ball", "dusk_ball", "quick_ball", "level_ball",
        "lure_ball", "moon_ball", "friend_ball", "love_ball", "fast_ball",
        "heavy_ball", "sport_ball", "safari_ball", "park_ball", "dream_ball",
        "beast_ball", "cherish_ball", "_ball$",
    ],
    "healing": [
        "potion", "revive", "antidote", "heal", "awakening", "energy_powder",
        "energy_root", "lemonade", "soda_pop", "fresh_water", "moomoo_milk",
        "full_restore",
    ],
    "apricorns": ["apricorn"],
    "berries": ["berry"],
    "evolution_items": [
        "stone", "scale", "dubious_disc", "protector", "electirizer",
        "magmarizer", "upgrade", "reaper_cloth", "whipped_dream", "sachet",
    ],
    "held_items": [
        "band", "specs", "scarf", "orb", "herb", "berry_juice", "lens",
        "rock", "incense",
    ],
}

CRAFTING_TABLE_TYPES = (
    "minecraft:crafting_shaped",
    "minecraft:crafting_shapeless",
    "minecraft:crafting_transmute",
    "minecraft:crafting_special",
)


def iter_recipe_jsons(jar_path: Path, namespace: str):
    prefixes = (f"data/{namespace}/recipe/", f"data/{namespace}/recipes/")
    if jar_path.is_dir():
        for prefix in prefixes:
            base = jar_path / prefix
            if base.exists():
                for p in base.rglob("*.json"):
                    try:
                        yield str(p), json.loads(p.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"  ! skipping unreadable {p}: {e}", file=sys.stderr)
    else:
        with zipfile.ZipFile(jar_path) as z:
            for name in z.namelist():
                if name.endswith(".json") and name.startswith(prefixes):
                    try:
                        yield name, json.loads(z.read(name).decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"  ! skipping unreadable {name}: {e}", file=sys.stderr)


def extract_result_item(recipe: dict):
    result = recipe.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("id") or result.get("item")
    return None


def classify(item_id: str, rules: dict):
    path = item_id.split(":", 1)[-1].lower()
    for group, keywords in rules.items():
        for kw in keywords:
            if kw.endswith("$"):
                if path.endswith(kw[:-1]):
                    return group
            elif kw in path:
                return group
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jar", required=True, help="Mod .jar, or an extracted mod/datapack folder")
    ap.add_argument("--namespace", required=True, help="Mod namespace to scan, e.g. cobblemon")
    ap.add_argument("--out", default=None, help="Output CSV (default: <namespace>.csv)")
    ap.add_argument("--rules", default=None, help="JSON file overriding the default group->keywords rules")
    args = ap.parse_args()

    jar_path = Path(args.jar)
    if not jar_path.exists():
        sys.exit(f"error: {jar_path} does not exist")

    rules = DEFAULT_RULES
    if args.rules:
        with open(args.rules, encoding="utf-8") as f:
            rules = json.load(f)

    items = {}  # item_id -> category ("" if none)
    seen = skipped = 0
    for _, recipe in iter_recipe_jsons(jar_path, args.namespace):
        seen += 1
        if recipe.get("type", "") not in CRAFTING_TABLE_TYPES:
            skipped += 1
            continue
        item_id = extract_result_item(recipe)
        if item_id:
            items[item_id] = classify(item_id, rules) or ""

    out = Path(args.out or f"{args.namespace}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "category"])
        for item_id in sorted(items):
            w.writerow([item_id, items[item_id]])

    blank = sum(1 for c in items.values() if not c)
    print(f"Scanned {seen} recipe file(s); {skipped} were non-crafting-table types (skipped).")
    print(f"Wrote {len(items)} item(s) to {out}  ({blank} uncategorized - fill in or leave blank to ignore)")
    counts = {}
    for c in items.values():
        if c:
            counts[c] = counts.get(c, 0) + 1
    for c, n in sorted(counts.items()):
        print(f"  [{c}] {n}")


if __name__ == "__main__":
    main()