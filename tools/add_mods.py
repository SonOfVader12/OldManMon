#!/usr/bin/env python3
"""
Read a mod list CSV, add each not-yet-installed mod to a packwiz pack,
and mark it as installed in the CSV.

CSV headers: Name, Site, Link, Server, Client, Installed, Category, Notes

Usage (from cmd / PowerShell):
    python add_mods.py mods.csv --pack "C:\\path\\to\\my-pack"
    python add_mods.py mods.csv --dry-run

Requires packwiz.exe on your PATH (or pass --packwiz "C:\\path\\packwiz.exe").
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

INSTALLED_VALUES = {"yes", "y", "true", "1", "x", "installed", "done", "✓", "✔"}
INSTALLED_MARK = "Yes"  # what gets written back after a successful add


def is_installed(value: str) -> bool:
    return (value or "").strip().lower() in INSTALLED_VALUES


def detect_platform(site: str, link: str):
    """Return 'modrinth', 'curseforge', or None."""
    host = urlparse(link).netloc.lower()
    if "modrinth.com" in host:
        return "modrinth"
    if "curseforge.com" in host:
        return "curseforge"
    s = (site or "").strip().lower()
    if "modrinth" in s:
        return "modrinth"
    if "curse" in s:
        return "curseforge"
    return None


def read_csv(path):
    # utf-8-sig strips the BOM that Excel adds
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Clean header names (e.g. "Link " -> "Link") but remember the originals
        original_headers = reader.fieldnames or []
        clean = {h: h.strip() for h in original_headers}
        rows = [{clean[k]: (v or "") for k, v in row.items() if k in clean} for row in reader]
    return list(clean.values()), rows


def write_csv(path, headers, rows):
    """Write atomically so a crash mid-write can't corrupt the CSV."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(suffix=".csv", dir=directory)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    except PermissionError:
        os.unlink(tmp)
        raise PermissionError(
            f"Can't write to {path}. Is it open in Excel? Close it and re-run."
        )
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_packwiz(packwiz, pack_dir, platform, link):
    cmd = [packwiz, platform, "add", link, "-y"]
    result = subprocess.run(
        cmd,
        cwd=pack_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description="Add mods from a CSV to a packwiz pack.")
    ap.add_argument("csv_file", help="Path to the mod list CSV")
    ap.add_argument("--pack", default=".", help="Path to the packwiz pack folder (contains pack.toml)")
    ap.add_argument("--packwiz", default="packwiz", help="Path to packwiz executable")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be done without running packwiz")
    args = ap.parse_args()

    packwiz = shutil.which(args.packwiz) or args.packwiz
    if not args.dry_run and not shutil.which(packwiz):
        sys.exit("packwiz not found. Add it to your PATH or use --packwiz <path-to-exe>.")

    pack_dir = os.path.abspath(args.pack)
    if not os.path.isfile(os.path.join(pack_dir, "pack.toml")):
        sys.exit(f"No pack.toml found in {pack_dir}. Use --pack to point at your pack folder.")

    headers, rows = read_csv(args.csv_file)
    for required in ("Name", "Link", "Installed"):
        if required not in headers:
            sys.exit(f"CSV is missing a '{required}' column. Found: {headers}")

    added, failed, skipped = [], [], []

    for row in rows:
        name = row.get("Name", "").strip() or "(unnamed)"
        link = row.get("Link", "").strip()

        if is_installed(row.get("Installed", "")):
            continue
        if not link:
            print(f"[skip] {name}: no link")
            skipped.append(name)
            continue

        platform = detect_platform(row.get("Site", ""), link)
        if platform is None:
            print(f"[skip] {name}: can't tell if Modrinth or CurseForge ({link})")
            skipped.append(name)
            continue

        print(f"[add ] {name} via {platform} ...", end=" ", flush=True)
        if args.dry_run:
            print("(dry run)")
            continue

        ok, output = run_packwiz(packwiz, pack_dir, platform, link)
        if ok:
            print("OK")
            row["Installed"] = INSTALLED_MARK
            added.append(name)
            write_csv(args.csv_file, headers, rows)  # save progress after each success
        else:
            print("FAILED")
            print("       " + output.replace("\n", "\n       "))
            failed.append(name)

    # Rebuild the index so packwiz.toml hashes are current
    if added and not args.dry_run:
        subprocess.run([packwiz, "refresh"], cwd=pack_dir)

    print("\n--- Summary ---")
    print(f"Added:   {len(added)}")
    print(f"Failed:  {len(failed)}" + (f"  -> {', '.join(failed)}" if failed else ""))
    print(f"Skipped: {len(skipped)}" + (f"  -> {', '.join(skipped)}" if skipped else ""))


if __name__ == "__main__":
    main()