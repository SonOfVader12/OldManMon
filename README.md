# <Pack Name>

A Minecraft modpack managed with [packwiz](https://packwiz.infra.link/).

- **Minecraft:** `<1.21.x>`
- **Mod loader:** `<Fabric / Quilt / NeoForge / Forge>` `<loader version>`
- **Pack URL:** `https://<your-host>/pack.toml`

> Replace every `<placeholder>` in this file with your own values, and update the pack URL to wherever you host this repo (see [Hosting](#hosting-the-pack)).

---

## Table of contents

- [Quick install (players)](#quick-install-players)
  - [Prism Launcher](#prism-launcher)
  - [MultiMC](#multimc)
  - [Other launchers / manual](#other-launchers--manual)
  - [Servers](#servers)
- [Installer flags](#installer-flags)
- [Maintaining the pack (developers)](#maintaining-the-pack-developers)
  - [Installing packwiz](#installing-packwiz)
  - [Common commands](#common-commands)
  - [Typical workflow](#typical-workflow)
  - [Exporting](#exporting)
- [Hosting the pack](#hosting-the-pack)
- [Troubleshooting](#troubleshooting)
- [Links](#links)

---

## Quick install (players)

Players don't need packwiz itself. They only need **packwiz-installer-bootstrap**, a small jar that downloads the latest pack contents every time the game launches, so updates are automatic.

| Tool | Download |
| --- | --- |
| packwiz-installer-bootstrap | https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest |
| packwiz-installer (fetched automatically by the bootstrap) | https://github.com/packwiz/packwiz-installer/releases/latest |

Download `packwiz-installer-bootstrap.jar` from the first link. You do **not** need to download the second one manually.

### Prism Launcher

1. Download and install [Prism Launcher](https://prismlauncher.org/download/).
2. Create a new instance with the **Minecraft version** and **mod loader** listed at the top of this README (leave it empty, with no mods).
3. Right-click the instance → **Folder** (or **Edit → Folder**) → open the `.minecraft` folder (called `minecraft` on some versions).
4. Place `packwiz-installer-bootstrap.jar` inside that folder.
5. Go to **Edit → Settings → Custom commands**, tick **Override global settings**, and set the **Pre-launch command** to:

   ```
   "$INST_JAVA" -jar packwiz-installer-bootstrap.jar https://<your-host>/pack.toml
   ```

6. Launch the instance. The installer window will open, download all mods and configs, then the game starts.

On every launch after that, the pack updates itself.

### MultiMC

Same steps as Prism Launcher. The setting is under **Settings → Custom commands → Pre-launch command**, and the command is identical.

### Other launchers / manual

Any launcher that can run a command before launching the game works the same way. If yours can't, you can run the installer by hand from inside the game's `.minecraft` directory:

```bash
java -jar packwiz-installer-bootstrap.jar https://<your-host>/pack.toml
```

Run it again whenever you want to update.

### Servers

Run this from the server directory (headless, server-side mods only):

```bash
java -jar packwiz-installer-bootstrap.jar -g -s server https://<your-host>/pack.toml
```

- `-g` disables the GUI (required on headless machines).
- `-s server` installs only mods marked as server-compatible.

Re-run it to update, then restart the server.

---

## Installer flags

Flags go between the jar name and the URL.

| Flag | Meaning |
| --- | --- |
| `-g` | No GUI (headless / console mode) |
| `-s client` | Install client-side mods only (the default on clients) |
| `-s server` | Install server-side mods only |
| `-s both` | Install everything regardless of side |
| `--pack-folder <dir>` | Install into a specific folder |
| `--meta-file <file>` | Where installer metadata is stored |

Example:

```bash
java -jar packwiz-installer-bootstrap.jar -g -s client https://<your-host>/pack.toml
```

---

## Maintaining the pack (developers)

### Installing packwiz

packwiz is a command-line tool.

**Option 1: prebuilt binaries**

Download the latest build for your OS from the GitHub Actions artifacts / nightly builds linked from the project:
https://github.com/packwiz/packwiz#installation

Put the executable somewhere on your `PATH`.

**Option 2: via Go** (requires [Go](https://go.dev/dl/) 1.19+)

```bash
go install github.com/packwiz/packwiz@latest
```

Make sure `$(go env GOPATH)/bin` is on your `PATH`, then verify:

```bash
packwiz --help
```

### Common commands

Run all commands from the repository root (where `pack.toml` lives).

| Command | What it does |
| --- | --- |
| `packwiz init` | Create a new pack (`pack.toml` and `index.toml`) |
| `packwiz modrinth add <name-or-url>` | Add a mod from Modrinth |
| `packwiz curseforge add <name-or-url>` | Add a mod from CurseForge |
| `packwiz url add <name> <url>` | Add a file from a direct URL |
| `packwiz list` | List all mods in the pack |
| `packwiz remove <mod>` | Remove a mod |
| `packwiz update <mod>` | Update one mod |
| `packwiz update --all` | Update every mod |
| `packwiz refresh` | Rebuild `index.toml` after manual file changes (run before committing) |
| `packwiz serve` | Serve the pack locally for testing (default `http://localhost:8080/pack.toml`) |
| `packwiz modrinth export` | Export a `.mrpack` for Modrinth |
| `packwiz curseforge export` | Export a CurseForge `.zip` |

Examples:

```bash
packwiz modrinth add sodium
packwiz modrinth add https://modrinth.com/mod/lithium
packwiz curseforge add jei
packwiz update --all
```

### Typical workflow

1. Make your change (`packwiz modrinth add ...`, edit configs under `config/`, etc.).
2. Run `packwiz refresh` so the index hashes are up to date.
3. Test locally with `packwiz serve`, pointing a test instance's pre-launch command at `http://localhost:8080/pack.toml`.
4. Commit and push:

   ```bash
   git add -A
   git commit -m "Add Sodium, update Lithium"
   git push
   ```

5. Players get the update automatically on their next launch.

### Exporting

If you also distribute the pack as a file instead of through the installer:

```bash
packwiz modrinth export     # produces <name>-<version>.mrpack
packwiz curseforge export   # produces <name>-<version>.zip
```

---

## Hosting the pack

packwiz needs the pack files (`pack.toml`, `index.toml`, and `mods/*.pw.toml`) served over plain HTTP(S). Two easy options for a GitHub repo:

**GitHub raw URL** (no setup):

```
https://raw.githubusercontent.com/<user>/<repo>/<branch>/pack.toml
```

**GitHub Pages** (recommended; better caching behavior and a cleaner URL):

1. Repo **Settings → Pages**, deploy from the `<branch>` branch, root folder.
2. Your pack URL becomes:

   ```
   https://<user>.github.io/<repo>/pack.toml
   ```

Use this URL everywhere `https://raw.githubusercontent.com/SonOfVader12/OldManMon/main/pack.toml` appears above.

---

## Troubleshooting

- **Installer says "Failed to download" or hash mismatch:** you probably forgot `packwiz refresh` before pushing. Run it, commit, push, and wait a minute for the host's cache to update.
- **Nothing happens on launch (Prism/MultiMC):** check that *Override global settings* is ticked under Custom commands, and that the jar is inside the instance's `.minecraft` folder, since the command runs relative to it.
- **Wrong Java picked up:** use `"$INST_JAVA"` (with quotes) in the Prism/MultiMC command rather than a bare `java`.
- **Mods missing on a server:** make sure you used `-s server`, and that the mod isn't marked client-only in its `.pw.toml` (`side = "client"`).
- **Stale files after removing a mod:** the installer deletes files it previously installed that are no longer in the pack. Files you added manually are left alone.

---

## Links

- packwiz: https://github.com/packwiz/packwiz
- packwiz documentation: https://packwiz.infra.link/
- packwiz-installer: https://github.com/packwiz/packwiz-installer
- packwiz-installer-bootstrap: https://github.com/packwiz/packwiz-installer-bootstrap
- Prism Launcher: https://prismlauncher.org/
- Modrinth: https://modrinth.com/
- CurseForge: https://www.curseforge.com/minecraft