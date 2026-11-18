# Changelog

## 1.0.2

- Basic and Advanced CPE settings with presets, IPE particle controls, solver
  iterations, particle budgets, simulation frequency and live engine readings.
- Optional NuttyMod Optimizer under Root. Requires active NuttyMod Root and
  Root Mode; its default is off. Forces native Fast CPE, or uses a compatibility
  preset for older supported engines.
- The optimizer preserves 120 Hz physics and caps particles at 800. Native
  solver iterations are capped at 12; the compatibility preset uses at most 6.
  Lower manual budgets take priority over these ceilings.
- Restore the captured game configuration on session exit and release the
  optimizer immediately when a Root dependency becomes inactive.
- Preserve existing preferences and keep CPE changes out of multiplayer.
- Build versioned 1.0.2 TAR/ZIP downloads and checksums; retain 1.0.0 artifacts.

## 1.0.0

- F8 menu, FPS and session HUD, pointer crosshair, keystrokes, solo palette,
  low gravity, half-speed physics and solo session actions.
- Local settings, deterministic Custom Cube package and installation through
  CPE Flasher Tool, with Windows and Linux checks.
