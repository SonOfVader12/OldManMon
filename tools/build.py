#!/usr/bin/env python3
"""
build.py - package the resource pack + datapack, publish a GitHub release, and
wire the datapack into your packwiz pack so the server picks it up on its normal
packwiz-installer run.

Works on Windows, Linux and macOS. Standard library only; it shells out to the
`gh` (GitHub CLI) and `packwiz` commands when you use --release.

Nothing private is stored in this file. Configure with arguments or environment
variables (arguments win):

  --repo          MC_PACK_REPO          GitHub "owner/name" (required for --release)
  --level-name    MC_LEVEL_NAME         world folder name, default "world"
  --datapack-file MC_DATAPACK_FILE      filename on the server, default "datapack.zip"
  --datapack-title MC_DATAPACK_TITLE    display name in the metafile, default "Datapack"

Usage:
  python build.py                          # build zips locally, print hashes
  python build.py --release --repo you/repo   # build + release + packwiz metafile + refresh

Repo layout (this script can live in the repo root or in tools/):
  pack/          packwiz pack (pack.toml, index.toml, mods/)
  resourcepack/  pack.mcmeta + assets/   (server-pushed via server.properties)
  datapack/      pack.mcmeta + data/     (delivered through packwiz, server side only)
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
FIXED_ZIP_DATE = (2020, 1, 1, 0, 0, 0)  # keeps zips reproducible when content is unchanged


def find_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "tools" else here


def hash_file(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_zip(src: Path, dest: Path) -> None:
    """Zip the *contents* of src so pack.mcmeta sits at the zip root."""
    if not (src / "pack.mcmeta").is_file():
        sys.exit(f"error: {src / 'pack.mcmeta'} not found")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    files = sorted(
        p for p in src.rglob("*")
        if p.is_file() and p.name not in SKIP_NAMES
    )
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            info = zipfile.ZipInfo(p.relative_to(src).as_posix(), FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())


def toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"error: '{name}' not found in PATH")


def run(cmd, **kwargs) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main() -> None:
    env = os.environ.get
    ap = argparse.ArgumentParser(description="Build and publish datapack + resource pack.")
    ap.add_argument("--release", action="store_true",
                    help="publish a GitHub release and update the packwiz pack")
    ap.add_argument("--repo", default=env("MC_PACK_REPO"),
                    help="GitHub owner/name (env: MC_PACK_REPO)")
    ap.add_argument("--level-name", default=env("MC_LEVEL_NAME", "world"),
                    help="server world folder name (env: MC_LEVEL_NAME, default: world)")
    ap.add_argument("--datapack-file", default=env("MC_DATAPACK_FILE", "datapack.zip"),
                    help="datapack filename on the server (env: MC_DATAPACK_FILE)")
    ap.add_argument("--datapack-title", default=env("MC_DATAPACK_TITLE", "Datapack"),
                    help="display name in the metafile (env: MC_DATAPACK_TITLE)")
    args = ap.parse_args()

    if args.release and not args.repo:
        sys.exit("error: --repo (or MC_PACK_REPO) is required with --release")
    if not args.datapack_file.endswith(".zip"):
        sys.exit("error: --datapack-file must end in .zip")

    root = find_root()
    pack_dir = root / "pack"
    dist = root / "dist"

    version = datetime.now().strftime("%Y%m%d-%H%M")
    tag = f"v{version}"
    rp_name = f"resourcepack-{version}.zip"
    rp_zip = dist / rp_name
    dp_zip = dist / args.datapack_file

    make_zip(root / "resourcepack", rp_zip)
    make_zip(root / "datapack", dp_zip)

    rp_sha1 = hash_file(rp_zip, "sha1")
    dp_sha256 = hash_file(dp_zip, "sha256")

    if args.release:
        require_tool("gh")
        require_tool("packwiz")
        if not (pack_dir / "pack.toml").is_file():
            sys.exit(f"error: {pack_dir / 'pack.toml'} not found")

        base_url = f"https://github.com/{args.repo}/releases/download/{tag}"
        rp_url = f"{base_url}/{rp_name}"
        dp_url = f"{base_url}/{args.datapack_file}"

        run([
            "gh", "release", "create", tag, str(rp_zip), str(dp_zip),
            "--repo", args.repo,
            "--title", f"Pack {version}",
            "--notes", f"Resource pack SHA-1: {rp_sha1}",
        ])

        # Lands at <level-name>/datapacks/<datapack-file> on the server
        meta_dir = pack_dir / args.level_name / "datapacks"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta = meta_dir / (args.datapack_file[:-4] + ".pw.toml")
        meta.write_text(
            f"name = {toml_str(args.datapack_title)}\n"
            f"filename = {toml_str(args.datapack_file)}\n"
            'side = "server"\n'
            "\n"
            "[download]\n"
            f"url = {toml_str(dp_url)}\n"
            'hash-format = "sha256"\n'
            f"hash = {toml_str(dp_sha256)}\n",
            encoding="utf-8",
            newline="\n",
        )

        run(["packwiz", "refresh"], cwd=pack_dir)

        print(f"\nDatapack metafile written: {meta.relative_to(root)}")
        print("Next: git add -A && git commit && git push, then run packwiz-installer on the server.")
    else:
        rp_url = f"https://github.com/<owner>/<repo>/releases/download/{tag}/{rp_name}"
        print("Built locally only (use --release to publish and update packwiz).")
        print(f"Datapack:      {dp_zip}  (sha256 {dp_sha256})")
        print(f"Resource pack: {rp_zip}  (sha1 {rp_sha1})")

    print("\nPut this in server.properties (the resource pack is NOT delivered via packwiz):")
    print(f"resource-pack={rp_url}")
    print(f"resource-pack-sha1={rp_sha1}")
    print("require-resource-pack=true")


if __name__ == "__main__":
    main()
