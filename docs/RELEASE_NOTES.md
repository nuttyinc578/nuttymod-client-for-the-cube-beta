NuttyMod Client 1.0.2 for The Cube Beta.

Get CPE Flasher Tool from https://nuttyinc578.github.io/CPE-flashing-tool/.
Download the client TAR, select it in **05 Custom Cube**, and rebuild with
Full rewrite enabled. The ZIP includes the TAR, installation guide, source,
license and a preview. SHA256SUMS.txt verifies the downloads.

Features: F8 client menu; FPS and session HUD; pointer crosshair; C/E/P/Space
keystrokes; mint, blue, lavender and pink shapes; solo low gravity and half-speed
physics; spawn eight shapes and clear shapes. Settings save locally in userdata.

New in 1.0.2:

- CPE Basic: Balanced, Quality and Custom presets, tuning toggle and IPE effects.
- CPE Advanced: solver iterations, particle budget, simulation rate and live
  engine values, with reset to game defaults.
- Root → NuttyMod Optimizer: optional, off by default, and available only with
  active NuttyMod Root and Root Mode. Forces native Fast CPE where supported,
  or a compatibility preset on older supported engines. Keeps 120 Hz physics,
  limits particle effects to at most 800, and reduces solver work.
- Existing local preferences migrate automatically. Game configuration and the
  shared Fast CPE state are restored when leaving solo play. Disabling the
  optimizer restores advanced tuning or game defaults.

The optimizer requires the matching Root package set in addition to the client.
Basic and advanced CPE tuning work without Root. Multiplayer keeps its existing
physics configuration. The original 1.0.0 downloads remain available.

Requires an original Cube Beta portable ZIP, matching complete game source,
unlocked CPELoader, userdata and Python 3.11+ with pygame, pymunk and PyInstaller.
Solo physics changes leave multiplayer's existing host/guest rules in place.
Restore backup in CPE Flasher Tool returns to the previous installation.
