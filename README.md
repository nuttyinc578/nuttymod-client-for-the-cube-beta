# NuttyMod Client for The Cube Beta

**Get [CPE Flasher Tool](https://nuttyinc578.github.io/CPE-flashing-tool/) to install NuttyMod Client.**

NuttyMod Client 1.0.0 adds an in-game F8 menu, HUD options, a mint palette and
solo physics controls to The Cube Beta. Install the client TAR using the
flasher's **05 Custom Cube** tab, then rebuild the game.

[Download client TAR](https://github.com/nuttyinc578/nuttymod-client-for-the-cube-beta/raw/refs/heads/main/downloads/NuttyMod-Client-1.0.0.tar)
· [Download ZIP with guide and preview](https://github.com/nuttyinc578/nuttymod-client-for-the-cube-beta/raw/refs/heads/main/downloads/NuttyMod-Client-1.0.0.zip)
· [SHA-256 checksums](downloads/SHA256SUMS.txt)
· [Installation guide](docs/INSTALL.md)

![NuttyMod Client's Display menu in The Cube Beta](docs/display.png)

## Features

- FPS counter, average frame time, shape count and session mode.
- Optional pointer crosshair and C/E/P/Space keystroke display.
- Mint, blue, lavender and pink shapes in solo play.
- Solo low gravity, half-speed physics, spawn eight shapes and clear shapes.
- Local settings at `userdata/nuttymod-client/settings.json`, with a reset button.
- About page linking to the CPE Flasher Tool website.

Physics changes and session actions apply to solo play. Multiplayer keeps the
game's existing host/guest physics rules. The client leaves CPELoader checks
and the flasher's update policy in place.

## Install

1. Get **[CPE Flasher Tool](https://nuttyinc578.github.io/CPE-flashing-tool/)**
   and download the client TAR above. If you download the ZIP, extract it first.
2. Keep an original official Cube Beta portable ZIP. Open your installed game,
   press **Ctrl+A**, choose **Y** to unlock CPELoader, then close the game.
3. Configure the flasher's original game ZIP, installed game folder, matching
   complete game source, Python compiler and userdata. Enable **Full rewrite**.
4. In **05 Custom Cube**, browse to `NuttyMod-Client-1.0.0.tar`.
5. Click **Flash ZIP + Recompile**, then install the completed build.
6. Launch the game, acknowledge the loader warnings, and press **F8**.

The rebuild requires Python 3.11+ with pygame, pymunk and PyInstaller.
The TAR contains client code; the game and compiler are separate downloads.
The client works with bundled Rephysics and optional CPE Series 2 — Ortain.
NuttyMod Root and the legacy isolated NuttyMod loader are not required.

## Controls

| Control | Action |
| --- | --- |
| F8 | Open or close NuttyMod Client |
| Esc while the menu is open | Close the client menu |
| Tab while the menu is open | Next page |
| Mouse | Select a page, toggle settings, or use solo session actions |

The simulation continues while the menu is open. The client consumes menu
clicks and keystrokes so they do not affect gameplay behind it.
F11 and CPELoader's Ctrl+A shortcut retain their existing behavior.

Use **Restore backup** in CPE Flasher Tool to return to the previous installation.

## Build and test

```sh
python tools/build.py
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

The builder uses Python's standard library. It creates the deterministic client
TAR, ZIP and checksums under `downloads/`. Tests use pygame with a headless display.
The GitHub Actions workflow tests the client and verifies the committed downloads
on Windows and Linux. The release workflow can publish matching assets when a
`v1.0.0` tag is pushed.

Source: [python/nuttymod_client.py](python/nuttymod_client.py).
The original repository's [CC0 license](LICENSE) is preserved.
