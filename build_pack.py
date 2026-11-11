#!/usr/bin/env python3
"""
build_pack.py  (step 2 of 2)

Takes one or more CSVs from scan_recipes.py (columns: item,category) and builds:

  <out>/datapack/data/<out-ns>/tags/item/<modid>_<category>.json   (item tags)
  <out>/resourcepack/assets/<out-ns>/crafting_tab_listing.json     (Legacy4J tabs)
  pack.mcmeta in each pack root (only if one doesn't already exist)

Each CSV becomes one crafting tab. The CSV file name (minus .csv) is the mod id,
so cobblemon.csv -> tab "cobblemon", tags like l4jcompat:cobblemon_pokeballs.
Rows with an empty category are ignored. Re-running regenerates each given
CSV's tags and tab, leaving other mods' tags/tabs in --out untouched.

USAGE
    python3 build_pack.py cobblemon.csv --tab-name cobblemon="Cobblemon" \\
        --icon-item cobblemon=cobblemon:poke_ball --out ./output
    python3 build_pack.py cobblemon.csv other_mod.csv --out ./output

Install: datapack/ -> <world>/datapacks/ ; resourcepack/ -> resourcepacks/
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

DATA_PACK_FORMAT = 48       # Minecraft 1.21.1
RESOURCE_PACK_FORMAT = 34   # Minecraft 1.21.1

SAFE = re.compile(r"[^a-z0-9_]+")


def read_csv(path: Path):
    """Return {category: set(items)} from a scan_recipes.py CSV."""
    groups = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            item = (row.get("item") or "").strip()
            cat = SAFE.sub("_", (row.get("category") or "").strip().lower()).strip("_")
            if not item or not cat:
                continue
            if ":" not in item:
                print(f"  ! {path}:{n} skipping '{item}' (no namespace)", file=sys.stderr)
                continue
            groups.setdefault(cat, set()).add(item)
    return groups


def merge_tab_listing(listing_path: Path, new_tab: dict):
    tabs = []
    if listing_path.exists():
        try:
            data = json.loads(listing_path.read_text(encoding="utf-8"))
            tabs = data if isinstance(data, list) else []
        except json.JSONDecodeError:
            print(f"  ! existing {listing_path} was invalid JSON, starting fresh", file=sys.stderr)
    tabs = [t for t in tabs if t.get("id") != new_tab["id"]]
    tabs.append(new_tab)
    listing_path.parent.mkdir(parents=True, exist_ok=True)
    listing_path.write_text(json.dumps(tabs, indent=4) + "\n", encoding="utf-8")


def write_mcmeta(root: Path, fmt: int, desc: str):
    root.mkdir(parents=True, exist_ok=True)
    p = root / "pack.mcmeta"
    if not p.exists():
        p.write_text(json.dumps({"pack": {"pack_format": fmt, "description": desc}}, indent=4) + "\n", encoding="utf-8")
        print(f"wrote {p}")


def parse_kv(values, what):
    out = {}
    for v in values or []:
        if "=" not in v:
            sys.exit(f"error: {what} must look like MODID=value, got '{v}'")
        k, val = v.split("=", 1)
        out[k.strip()] = val.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csvs", nargs="+", help="CSV file(s) from scan_recipes.py")
    ap.add_argument("--out", default="./output", help="Output directory (default: ./output)")
    ap.add_argument("--out-namespace", default="l4jcompat", help="Namespace for generated tags/listing (default: l4jcompat)")
    ap.add_argument("--tab-name", action="append", metavar="MODID=Name", help="Display name for a tab (repeatable). Default: title-cased mod id")
    ap.add_argument("--icon-item", action="append", metavar="MODID=item", help="Icon item for a tab (repeatable). Default: first item of first category")
    args = ap.parse_args()

    names = parse_kv(args.tab_name, "--tab-name")
    icons = parse_kv(args.icon_item, "--icon-item")

    out_dir = Path(args.out)
    ns = args.out_namespace
    tag_dir = out_dir / "datapack" / "data" / ns / "tags" / "item"
    listing_path = out_dir / "resourcepack" / "assets" / ns / "crafting_tab_listing.json"

    tag_dir.mkdir(parents=True, exist_ok=True)

    for csv_arg in args.csvs:
        csv_path = Path(csv_arg)
        if not csv_path.exists():
            sys.exit(f"error: {csv_path} does not exist")
        mod_id = SAFE.sub("_", csv_path.stem.lower()).strip("_")
        groups = read_csv(csv_path)
        if not groups:
            print(f"{csv_path}: no categorized items, skipping")
            continue

        # clear this mod's old tags so removed categories don't linger
        for old in tag_dir.glob(f"{mod_id}_*.json"):
            old.unlink()

        tag_names = []
        for cat, items in sorted(groups.items()):
            tag_name = f"{mod_id}_{cat}"
            (tag_dir / f"{tag_name}.json").write_text(
                json.dumps({"values": sorted(items)}, indent=4) + "\n", encoding="utf-8")
            tag_names.append((cat, tag_name))
            print(f"[{mod_id}] {cat}: {len(items)} item(s)")

        icon = icons.get(mod_id) or sorted(groups[sorted(groups)[0]])[0]
        tab_name = names.get(mod_id) or mod_id.replace("_", " ").title()
        merge_tab_listing(listing_path, {
            "id": f"{ns}:{mod_id}",
            "icon": {"type": "item", "value": {"item": icon}},
            "name": {"translate": f"legacy.container.tab.{mod_id}", "fallback": tab_name},
            "listing": [{"group": c, "recipes": [f"#{ns}:{t}"]} for c, t in tag_names],
        })
        print(f"[{mod_id}] tab '{ns}:{mod_id}' ('{tab_name}', icon {icon})")

    write_mcmeta(out_dir / "datapack", DATA_PACK_FORMAT, "Legacy4J crafting tab tags")
    write_mcmeta(out_dir / "resourcepack", RESOURCE_PACK_FORMAT, "Legacy4J crafting tab listing")
    print(f"\nDone. datapack -> world/datapacks/ ; resourcepack -> resourcepacks/  (from {out_dir})")


if __name__ == "__main__":
    main()