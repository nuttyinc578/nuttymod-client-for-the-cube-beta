import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
builder = runpy.run_path(str(ROOT/'tools'/'build.py'))['build_package']
distribution_builder = runpy.run_path(str(ROOT/'tools'/'build.py'))['build_distribution']
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
try:
    import pygame
except ImportError:
    pygame = None


class ClientPackageTests(unittest.TestCase):
    def test_distribution_is_reproducible_and_has_matching_downloads(self):
        import zipfile
        with tempfile.TemporaryDirectory() as folder:
            package, bundle = distribution_builder(Path(folder)/'a')
            _, second = distribution_builder(Path(folder)/'b')
            self.assertEqual(bundle.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(bundle) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read(package.name), package.read_bytes())
                self.assertIn(b'05 Custom Cube', archive.read('INSTALL.md'))
                self.assertEqual(archive.read('LICENSE'), (ROOT/'LICENSE').read_bytes())
            checksums = (package.parent/'SHA256SUMS.txt').read_text().splitlines()
            for line in checksums:
                checksum, name = line.split('  ')
                self.assertEqual(hashlib.sha256((package.parent/name).read_bytes()).hexdigest(), checksum)

    def test_deterministic_package_with_matching_inventory_and_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            first = builder(Path(folder)/'a')
            second = builder(Path(folder)/'b')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            expected = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual(first.with_suffix('.tar.sha256').read_text().split()[0], expected)
            with tarfile.open(first) as archive:
                manifest = json.load(archive.extractfile('custom-cube.json'))
                self.assertEqual(manifest['name'], 'NuttyMod Client')
                self.assertEqual(manifest['api'], 'CubeBeta/1')
                for name, checksum in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.extractfile(name).read()).hexdigest(), checksum)
                self.assertEqual(set(archive.getnames()), {'custom-cube.json', *manifest['files']})



@unittest.skipIf(pygame is None, 'pygame is needed for client runtime tests')
class ClientRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        spec = importlib.util.spec_from_file_location('client_test', ROOT/'python'/'nuttymod_client.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = SimpleNamespace(
            screen=pygame.display.set_mode((1100, 720)), clock=pygame.time.Clock(),
            common_events=mock.Mock(return_value=True), draw_toast=mock.Mock(),
            run_simulation=mock.Mock(), draw_game_hud=mock.Mock(),
            cpeloader=SimpleNamespace(require_flash=mock.Mock()),
        )
        self.client = self.module.NuttyModClient(self.app, self.temp.name)

    def key(self, key):
        return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)

    def test_menu_consumes_input_and_escape_does_not_leave_game(self):
        self.client.install()
        events = [self.key(pygame.K_F8), pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 400))]
        self.assertTrue(self.app.common_events(events))
        self.assertTrue(self.client.open)
        self.assertEqual(events, [])
        events = [self.key(pygame.K_ESCAPE), self.key(pygame.K_c)]
        self.app.common_events(events)
        self.assertFalse(self.client.open)
        self.assertEqual(events, [])
        events = [self.key(pygame.K_c)]
        self.app.common_events(events)
        self.assertEqual(len(events), 1)

    def test_quit_and_original_common_events_are_preserved(self):
        common = self.app.common_events
        self.client.install()
        common.return_value = False
        self.client.open = True
        events = [pygame.event.Event(pygame.QUIT)]
        self.assertFalse(self.app.common_events(events))
        common.assert_called_once_with(events)

    def test_settings_persist_reset_and_invalid_values_are_ignored(self):
        self.client.activate('crosshair')
        restored = self.module.NuttyModClient(self.app, self.temp.name)
        self.assertTrue(restored.settings['crosshair'])
        restored.activate('reset')
        self.assertEqual(json.loads(restored.path.read_text())['crosshair'], False)
        restored.path.write_text('{"schema": 1, "fps": "false", "low_gravity": true, "extra": true}')
        restored = self.module.NuttyModClient(self.app, self.temp.name)
        self.assertTrue(restored.settings['fps'])
        self.assertTrue(restored.settings['low_gravity'])
        self.assertNotIn('extra', restored.settings)
        restored.path.write_text('[]')
        self.assertEqual(self.module.NuttyModClient(self.app, self.temp.name).settings, self.module.DEFAULTS)

    def test_physics_is_solo_only_and_hooks_restore_even_on_failure(self):
        class World:
            def __init__(self): self.entities = {}
            def update(self, dt, wind=0, gravity_scale=1): return dt, wind, gravity_scale
            def spawn(self, x, y, owner='host', spec=None, color=None): return color

        update, spawn = World.update, World.spawn
        observations = []

        def simulate(peer=None, is_host=True):
            world = World()
            observations.append((world.update(.02, 3, 2), world.spawn(20, 30)))
            raise RuntimeError('leave session')

        self.app.run_simulation = simulate
        self.client.settings.update(low_gravity=True, slow_motion=True)
        self.client.install()
        with mock.patch.dict(sys.modules, {'cube_core': SimpleNamespace(PhysicsWorld=World)}):
            with self.assertRaisesRegex(RuntimeError, 'leave session'):
                self.app.run_simulation()
            self.assertEqual(observations[-1][0], (.01, 3, .5))
            self.assertIn(observations[-1][1], self.module.PALETTE)
            self.assertIs(World.update, update)
            self.assertIs(World.spawn, spawn)
            with self.assertRaisesRegex(RuntimeError, 'leave session'):
                self.app.run_simulation(peer=object())
            self.assertEqual(observations[-1], ((.02, 3, 2), None))
        self.assertFalse(self.client.in_simulation)
        self.assertIsNone(self.client.world)

    def test_menu_clicks_use_layout_and_solo_actions_are_guarded(self):
        self.client.open = True
        rect = next(rect for rect, action in self.client.controls() if action == 'crosshair')
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)]
        self.client.handle_events(events)
        self.assertTrue(self.client.settings['crosshair'])
        self.assertEqual(events, [])
        self.client.world = mock.Mock()
        self.client.activate('clear')
        self.client.world.clear.assert_not_called()
        self.client.in_simulation = True
        self.client.activate('rain')
        self.assertEqual(self.client.world.spawn.call_count, 8)
        self.client.multiplayer = True
        self.client.activate('clear')
        self.client.world.clear.assert_not_called()
        self.client.tab = 'Physics'
        self.client.activate('low_gravity')
        self.assertFalse(self.client.settings['low_gravity'])

    def test_all_pages_and_hud_render_and_repeated_startup_is_idempotent(self):
        self.module.game_root = self.temp.name
        self.addCleanup(lambda: self.module.__dict__.pop('game_root', None))
        self.module.on_load(self.app, {'schema': 1})
        client = self.app.nuttymod_client
        common = self.app.common_events
        self.module.on_load(self.app, {'schema': 1})
        self.assertIs(self.app.common_events, common)
        for tab in ('Display', 'Physics', 'About'):
            client.tab, client.open = tab, True
            self.app.draw_toast()
        client.in_simulation, client.open = True, False
        client.settings.update(crosshair=True, keys=True)
        self.app.draw_game_hud(12)
        self.app.draw_toast()
        self.assertEqual(client.shape_count, 12)
        self.app.cpeloader.require_flash.assert_called_once()


if __name__ == '__main__':
    unittest.main()
