"""Offline real-game smoke test; Root availability is supplied as a test fixture."""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game-source', type=Path, required=True)
parser.add_argument('--output', type=Path, default=ROOT/'docs')
args = parser.parse_args()
source, output = args.game_source.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                  PYGAME_HIDE_SUPPORT_PROMPT='1', CPE_DISABLE_BRIDGE='1')

with tempfile.TemporaryDirectory(prefix='nuttymod-102-') as folder:
    stage = Path(folder)
    for path in source.iterdir():
        if path.is_file() and (path.suffix in {'.py', '.rb', '.js', '.png', '.ico', '.txt'} or path.name in (
                'cpe-backend.json', 'nightly-config.json', 'click.mp3', 'fall_music.mp3')):
            if not path.name.startswith(('test_', '.')):
                shutil.copy2(path, stage/path.name)
    for name in ('cpe', 'cpe_rephysics', 'cube_launcher', 'themes'):
        if (source/name).is_dir():
            shutil.copytree(source/name, stage/name, ignore=shutil.ignore_patterns('__pycache__', 'tests', 'bin', 'obj'))
    sys.path.insert(0, str(stage))
    import pygame
    import cube_core
    from cpeloader import CPELoader
    from cpe.performance import fast_enabled
    import the_cube_beta_summer as game
    CPELoader(stage).unlock()
    with mock.patch.object(game, 'AddonManager', return_value=SimpleNamespace(shapes=[], events=[])):
        app = game.GameApp()
    module = runpy.run_path(str(ROOT/'python'/'nuttymod_client.py'), init_globals={'game_root': stage})
    module['on_load'](app, {'schema': 1})
    client = app.nuttymod_client
    assert not client.root_ready()
    client.activate('optimizer')
    assert not client.settings['optimizer']
    original_update, original_spawn = cube_core.PhysicsWorld.update, cube_core.PhysicsWorld.spawn
    draw, frames, captured = app.draw_toast, [0], []

    def draw_frame():
        frames[0] += 1
        frame = frames[0]
        if frame == 1:
            client.tab, client.open = 'Root', True
        if frame == 2:
            pygame.image.save(app.screen, str(output/'root-locked.png'))
            client.open = False
            # These flags model a successful, verified Root/Root Mode startup.
            # The test never installs Root or changes the user's game.
            app.nuttymod_root_enabled = app.root_mode_enabled = True
            client.activate('optimizer')
            assert client.optimizer_active and fast_enabled() and client.world.cpe.fast_mode
            assert client.world.space.iterations == 12
            assert client.world.cpe.particles.max_particles == 800
            client.activate('rain')
            client.activate('cycle:cpe_preset')
            captured.append(client.world.cpe)
        if 12 <= frame <= 17:
            client.open, client.tab = True, module['TABS'][frame-12]
        if frame == 18:
            client.open = False
        draw()
        if 12 <= frame <= 17:
            pygame.image.save(app.screen, str(output/(client.tab.lower().replace(' ', '-')+'.png')))
        if frame == 18:
            pygame.image.save(app.screen, str(output/'gameplay.png'))
        if frame == 19:
            app.root_mode_enabled = False
            client.configure_cpe()
            assert not client.optimizer_active and not fast_enabled()
            assert not client.world.cpe.fast_mode
            assert client.world.cpe.particles.max_particles == 1600
        if frame == 20:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))

    app.draw_toast = draw_frame
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(320, 200)))
    app.run_simulation()
    assert frames[0] == 20 and client.shape_count == 9
    assert cube_core.PhysicsWorld.update is original_update and cube_core.PhysicsWorld.spawn is original_spawn
    assert not fast_enabled() and not captured[0].fast_mode
    assert captured[0].space.iterations == 20 and captured[0].particles.max_particles == 4000
    assert not client.in_simulation and client.world is None
    # Exercise the independent solver's compatibility preset as well.
    from cpe_rephysics.engine import CubePhysicsEngine
    engine = CubePhysicsEngine()
    engine.execute_line('CPE/1 1 2 200 100 20 1 255 90 30')
    state = module['CPEConfiguration'](engine)
    assert state.apply(module['DEFAULTS'], True)
    engine.step(1/60)
    assert engine.space.iterations == 6 and engine.particles.max_particles == 800
    assert engine.snapshot()['bodies']
    state.restore()
    assert engine.space.iterations == 20 and engine.particles.max_particles == 4000
    pygame.quit()
    report = {'client_version': module['VERSION'], 'real_game_frames': frames[0], 'shapes': client.shape_count,
              'native_fast_cpe': True, 'rephysics_compatibility': True, 'root_gate': True,
              'root_revocation_restored_manual_settings': True, 'session_configuration_restored': True,
              'root_availability_test_fixture': True, 'network_used': False}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))
