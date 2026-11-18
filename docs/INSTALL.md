# Installing NuttyMod Client 1.0.2

Get **CPE Flasher Tool** at <https://nuttyinc578.github.io/CPE-flashing-tool/>.

1. Download `NuttyMod-Client-1.0.2.tar` from this repository's `downloads` folder.
   If you download the ZIP instead, extract it to get the TAR and this guide.
2. Keep an original official Cube Beta portable ZIP. Open the installed game,
   press **Ctrl+A**, choose **Y** to unlock CPELoader, then close the game.
3. Open CPE Flasher Tool and select the original ZIP, installed game folder,
   matching complete game source, and Python 3.11+ with pygame, pymunk and PyInstaller.
4. In **02 Userdata**, choose or create userdata. Leave **Full rewrite** enabled.
5. In **05 Custom Cube**, browse to `NuttyMod-Client-1.0.2.tar`.
   Select the 1.0.2 TAR even if the flasher also offers an older bundled client.
   Bundled Rephysics works; CPE Series 2 — Ortain is optional.
6. Trust the selected inputs, click **Flash ZIP + Recompile**, and install the
   completed build. Launch the game and acknowledge the loader warnings.
7. Press **F8** to open NuttyMod Client. F8 or Esc closes it; Tab changes page.

The Display page controls FPS, statistics, crosshair, keystrokes and the solo
palette. The Physics page offers solo low gravity, half-speed physics, spawn
eight shapes and clear shapes. **CPE Basic** enables custom tuning, presets and
particles. **CPE Advanced** changes solver iterations, particle budget and
simulation rate. The About page has the flasher link and a settings reset button.

## Optional NuttyMod Optimizer

The client works without Root. To use **Root → NuttyMod Optimizer**, install both
**NuttyMod Root** and **Root Mode** using the flasher's matching Root package set,
and select the client TAR in the same rebuild. See the flasher's
[Root guide](https://github.com/nuttyinc578/CPE-flashing-tool/blob/main/NUTTYMOD_ROOT.md).

Open **F8 → Root** after installation. Both dependencies must show **ACTIVE**.
The optimizer is off by default and cannot be enabled while either is missing.
It forces Fast CPE in solo play, with 120 Hz physics and a particle budget of up
to 800. Older engines use a compatibility preset. It overrides higher advanced
budgets until disabled, then restores your manual tuning or game defaults.
Leaving solo play restores the previous shared Fast CPE setting as well.

Settings save locally at `userdata/nuttymod-client/settings.json`. Physics keeps
running while the menu is open. Its clicks and keystrokes are consumed by the
menu, and F11 / Ctrl+A keep their existing game behavior.

Physics changes, shape palette and session actions apply only to solo play.
Multiplayer keeps the game's existing host/guest physics rules. The client does
not require the legacy isolated NuttyMod loader.

To remove the flashed installation, use **Restore backup** in CPE Flasher Tool.
