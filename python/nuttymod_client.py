"""NuttyMod Client: an explicit CubeBeta/1 startup hook for CPE Flasher Tool."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import MethodType

import pygame

VERSION = '1.0.2'
FLASHER_URL = 'https://nuttyinc578.github.io/CPE-flashing-tool/'
ROOT_GUIDE_URL = 'https://github.com/nuttyinc578/CPE-flashing-tool/blob/main/NUTTYMOD_ROOT.md'
TABS = ('Display', 'Physics', 'CPE Basic', 'CPE Advanced', 'Root', 'About')
CPE_DEFAULTS = {
    'cpe_enabled': False, 'cpe_particles': True, 'cpe_preset': 'Custom',
    'cpe_iterations': 20, 'cpe_particle_limit': 4000, 'cpe_step_hz': 120,
}
CHOICES = {
    'cpe_preset': ('Balanced', 'Quality', 'Custom'),
    'cpe_iterations': (4, 8, 12, 20, 30),
    'cpe_particle_limit': (0, 200, 800, 1600, 4000),
    'cpe_step_hz': (60, 120, 240),
}
DEFAULTS = {
    'fps': True, 'stats': True, 'crosshair': False, 'keys': False,
    'neon': True, 'low_gravity': False, 'slow_motion': False,
    **CPE_DEFAULTS, 'optimizer': False,
}
PALETTE = ((111, 245, 193), (118, 195, 255), (185, 157, 255), (255, 178, 211))
BG, CARD, LINE = (13, 20, 29), (22, 32, 43), (42, 57, 70)
TEXT, MUTED, ACCENT = (236, 245, 246), (143, 163, 176), PALETTE[0]


class CPEConfiguration:
    """Own temporary settings for one engine, retaining its original configuration."""
    def __init__(self, engine):
        self.engine = engine
        self.space = getattr(engine, 'space', None)
        self.particles = getattr(engine, 'particles', None)
        self.supported = (self.space is not None and hasattr(self.space, 'iterations')
                          and self.particles is not None and hasattr(self.particles, 'max_particles'))
        self.active = False
        self.forced_fast = False
        self.native_fast = callable(getattr(engine, 'set_fast_mode', None))
        self.original = {}
        self.capture()

    def capture(self):
        if self.supported:
            self.original = {'iterations': self.space.iterations, 'particles': self.particles.max_particles,
                             'fast': getattr(self.engine, 'fast_mode', False),
                             'step': getattr(self.engine, '_fixed_step', None)}

    def restore(self):
        if not self.active:
            return
        if self.forced_fast and self.native_fast:
            self.engine.set_fast_mode(self.original['fast'])
        self.space.iterations = self.original['iterations']
        self.particles.max_particles = self.original['particles']
        if self.original['step'] is not None:
            self.set_step(self.original['step'])
        self.active = self.forced_fast = False

    def set_step(self, value):
        if getattr(self.engine, '_fixed_step', None) != value:
            self.engine._fixed_step = value
            if hasattr(self.engine, '_accumulator'):
                self.engine._accumulator = 0.0

    def apply(self, settings, optimizer):
        if not self.supported:
            return False
        if not settings['cpe_enabled'] and not optimizer:
            self.restore()
            return False
        if self.forced_fast and not optimizer and self.native_fast:
            self.engine.set_fast_mode(self.original['fast'])
        self.active = True
        self.forced_fast = optimizer
        iterations = settings['cpe_iterations'] if settings['cpe_enabled'] else self.original['iterations']
        limit = settings['cpe_particle_limit'] if settings['cpe_enabled'] else self.original['particles']
        step = 1/settings['cpe_step_hz'] if settings['cpe_enabled'] else self.original['step']
        if optimizer:
            if self.native_fast:
                # Reassert the mode if another game control switches it off.
                if getattr(self.engine, 'fast_mode', None) is not True:
                    self.engine.set_fast_mode(True)
            iterations = min(iterations, 12 if self.native_fast else 6)
            limit = min(limit, self.original['particles'], 800)
            step = 1/120
        if settings['cpe_enabled'] and not settings['cpe_particles']:
            limit = 0
        self.space.iterations = iterations
        self.particles.max_particles = limit
        live_particles = getattr(self.particles, 'particles', None)
        if isinstance(live_particles, list) and len(live_particles) > limit:
            del live_particles[limit:]
        if self.original['step'] is not None:
            self.set_step(step)
        return optimizer


class NuttyModClient:
    def __init__(self, app, root):
        self.app = app
        self.path = Path(root)/'userdata'/'nuttymod-client'/'settings.json'
        self.settings = dict(DEFAULTS)
        try:
            if self.path.stat().st_size <= 65536:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data.get('schema') == 1:
                    for key, default in DEFAULTS.items():
                        value = data.get(key)
                        if type(value) is type(default) and (key not in CHOICES or value in CHOICES[key]):
                            self.settings[key] = value
        except (OSError, ValueError):
            pass
        self.open = False
        self.tab = 'Display'
        self.in_simulation = False
        self.multiplayer = False
        self.world = None
        self.shape_count = 0
        self.held = set()
        self.fonts = {}
        self.status = 'Settings save locally in userdata.'
        self.engine_states = []
        self.optimizer_active = False
        self._performance = None
        self._performance_checked = False
        self._previous_fast = None

    def root_ready(self):
        return (getattr(self.app, 'nuttymod_root_enabled', False) is True
                and getattr(self.app, 'root_mode_enabled', False) is True)

    def optimizer_status(self):
        if not self.settings['optimizer']:
            return 'OFF'
        if not self.root_ready():
            return 'LOCKED: ROOT COMPONENTS REQUIRED'
        if self.multiplayer:
            return 'SOLO PLAY ONLY'
        if self.optimizer_active:
            return 'FAST CPE ACTIVE'
        if self.in_simulation and self.world is not None:
            return 'UNSUPPORTED CPE ENGINE'
        return 'WAITING FOR SOLO PLAY'

    def sync_fast_mode(self, enabled):
        if enabled and not self._performance_checked:
            import importlib
            self._performance_checked = True
            try:
                module = importlib.import_module('cpe.performance')
                if callable(getattr(module, 'fast_enabled', None)) and callable(getattr(module, 'set_fast_mode', None)):
                    self._performance = module
            except ImportError:
                pass  # Older engines use the per-engine compatibility preset.
        if self._performance is None:
            return
        if enabled:
            if self._previous_fast is None:
                self._previous_fast = self._performance.fast_enabled()
            if not self._performance.fast_enabled():
                self._performance.set_fast_mode(True)
        elif self._previous_fast is not None:
            self._performance.set_fast_mode(self._previous_fast)
            self._previous_fast = None

    def configure_cpe(self):
        self.optimizer_active = False
        if not self.in_simulation or self.multiplayer or self.world is None:
            self.sync_fast_mode(False)
            return
        engine = getattr(self.world, 'cpe', None)
        if engine is None:
            return
        state = next((item for item in self.engine_states if item.engine is engine), None)
        if state is None:
            state = CPEConfiguration(engine)
            self.engine_states.append(state)
        optimizer = self.settings['optimizer'] and self.root_ready() and state.supported
        # Capture the engine before the native global mode changes its settings.
        if state.supported and not state.active and (optimizer or self.settings['cpe_enabled']):
            state.capture()
        self.sync_fast_mode(optimizer)
        self.optimizer_active = state.apply(self.settings, optimizer)

    def restore_cpe(self):
        try:
            self.sync_fast_mode(False)
        finally:
            for state in self.engine_states:
                state.restore()
            self.engine_states.clear()
            self.optimizer_active = False

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'schema': 1, **self.settings}, indent=2)+'\n', encoding='utf-8', newline='\n')
            os.replace(temporary, self.path)
            self.status = 'Settings saved.'
        except OSError:
            self.status = 'Could not save settings. Changes apply for this session.'

    def install(self):
        app = self.app
        common, toast = app.common_events, app.draw_toast
        simulation, hud = app.run_simulation, app.draw_game_hud
        client = self

        def common_events(app, events):
            # The loader handles its reserved shortcuts before client input.
            if not common(events):
                return False
            client.handle_events(events)
            return True

        def draw_toast(app):
            client.draw()
            # Keep existing toasts and required integrity messages visible.
            return toast()

        def draw_hud(app, *args, **kwargs):
            client.shape_count = args[0] if args else kwargs.get('shape_count', 0)
            return hud(*args, **kwargs)

        def run_simulation(app, peer=None, is_host=True):
            import cube_core
            client.in_simulation = True
            client.multiplayer = peer is not None
            client.world = None
            client.shape_count = 0
            world_type = cube_core.PhysicsWorld
            update, spawn = world_type.update, world_type.spawn

            def update_world(world, dt, wind=0, gravity_scale=1):
                client.world = world
                client.configure_cpe()
                speed = .5 if client.settings['slow_motion'] else 1
                gravity = .25 if client.settings['low_gravity'] else 1
                return update(world, dt*speed, wind, gravity_scale*gravity)

            def spawn_shape(world, x, y, owner='host', spec=None, color=None):
                if client.settings['neon'] and color is None:
                    color = PALETTE[len(world.entities) % len(PALETTE)]
                return spawn(world, x, y, owner, spec, color)

            # Multiplayer keeps the game's existing host/guest physics rules.
            if not client.multiplayer:
                world_type.update, world_type.spawn = update_world, spawn_shape
            try:
                return simulation(peer=peer, is_host=is_host)
            finally:
                if not client.multiplayer:
                    world_type.update, world_type.spawn = update, spawn
                client.in_simulation = False
                client.multiplayer = False
                try:
                    client.restore_cpe()
                finally:
                    client.world = None
                    client.held.clear()

        app.common_events = MethodType(common_events, app)
        app.draw_toast = MethodType(draw_toast, app)
        app.draw_game_hud = MethodType(draw_hud, app)
        app.run_simulation = MethodType(run_simulation, app)
        app.nuttymod_client = self
        app.nuttymod_client_enabled = True
        app.custom_cube_name = 'NuttyMod Client'
        pygame.display.set_caption('NuttyMod Client '+VERSION+' | The Cube Beta')

    def handle_events(self, events):
        remaining = []
        blocked = self.open
        for event in events:
            if event.type == pygame.WINDOWFOCUSLOST:
                self.held.clear()
            elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if event.type == pygame.KEYDOWN:
                    self.held.add(event.key)
                else:
                    self.held.discard(event.key)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                blocked = True
                if not getattr(event, 'repeat', False):
                    self.open = not self.open
                continue
            if self.open:
                blocked = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.open = False
                    elif event.key == pygame.K_TAB:
                        self.tab = TABS[(TABS.index(self.tab)+1) % len(TABS)]
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in self.controls():
                        if rect.collidepoint(event.pos):
                            self.activate(action)
                            break
                if event.type in (pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                                  pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                    continue
            if blocked and event.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN,
                                          pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                continue
            remaining.append(event)
        events[:] = remaining

    def layout(self):
        width, height = self.app.screen.get_size()
        panel = pygame.Rect(0, 0, min(780, width-32), min(560, height-40))
        panel.center = (width//2, height//2)
        return panel, panel.x+200, panel.y+112, panel.width-224

    def controls(self):
        panel, x, y, width = self.layout()
        controls = [(pygame.Rect(panel.right-54, panel.y+24, 30, 30), 'close')]
        controls += [(pygame.Rect(panel.x+18, panel.y+112+i*50, 158, 40), 'tab:'+tab)
                     for i, tab in enumerate(TABS)]
        names = ('fps', 'stats', 'crosshair', 'keys', 'neon') if self.tab == 'Display' else (
            ('low_gravity', 'slow_motion') if self.tab == 'Physics' else ())
        controls += [(pygame.Rect(x, y+i*64, width, 54), name) for i, name in enumerate(names)]
        if self.tab == 'Physics':
            controls += [(pygame.Rect(x, y+150+i*54, width, 44), action)
                         for i, action in enumerate(('rain', 'clear'))]
        if self.tab == 'CPE Basic':
            controls += [(pygame.Rect(x, y+i*64, width, 54), action)
                         for i, action in enumerate(('cpe_enabled', 'cycle:cpe_preset', 'cpe_particles'))]
            controls.append((pygame.Rect(x, y+208, width, 44), 'reset-cpe'))
        if self.tab == 'CPE Advanced':
            controls += [(pygame.Rect(x, y+i*64, width, 54), 'cycle:'+key)
                         for i, key in enumerate(('cpe_iterations', 'cpe_particle_limit', 'cpe_step_hz'))]
            controls.append((pygame.Rect(x, y+208, width, 44), 'reset-cpe'))
        if self.tab == 'Root':
            controls += [(pygame.Rect(x, y, width, 54), 'optimizer'),
                         (pygame.Rect(x, y+268, width, 44), 'root-guide')]
        if self.tab == 'About':
            controls += [(pygame.Rect(x, y+202+i*54, width, 44), action)
                         for i, action in enumerate(('flasher', 'reset'))]
        return controls

    def activate(self, action):
        key = action.removeprefix('cycle:')
        if self.multiplayer and (key in CPE_DEFAULTS or key in ('optimizer', 'reset-cpe', 'low_gravity', 'slow_motion')):
            self.status = 'CPE and physics controls are available in solo play.'
            return
        if action == 'optimizer' and not self.root_ready() and not self.settings['optimizer']:
            self.status = 'Optimizer requires active NuttyMod Root + Root Mode.'
            return
        if action == 'close':
            self.open = False
        elif action.startswith('tab:'):
            if action[4:] in TABS:
                self.tab = action[4:]
        elif action.startswith('cycle:') and key in CHOICES:
            choices = CHOICES[key]
            self.settings[key] = choices[(choices.index(self.settings[key])+1) % len(choices)]
            self.settings['cpe_enabled'] = True
            if key == 'cpe_preset' and self.settings[key] != 'Custom':
                iterations, limit = (12, 1600) if self.settings[key] == 'Balanced' else (30, 4000)
                self.settings.update(cpe_iterations=iterations, cpe_particle_limit=limit, cpe_step_hz=120)
            elif key != 'cpe_preset':
                self.settings['cpe_preset'] = 'Custom'
            self.save()
            self.configure_cpe()
        elif action == 'reset-cpe':
            self.settings.update(CPE_DEFAULTS)
            self.save()
            self.configure_cpe()
        elif action in DEFAULTS:
            if self.tab == 'Physics' and self.multiplayer:
                self.status = 'Physics controls are available in solo play.'
                return
            self.settings[action] = not self.settings[action]
            self.save()
            self.configure_cpe()
        elif action in ('rain', 'clear'):
            if not self.in_simulation or self.multiplayer or self.world is None:
                self.status = 'Start a solo game to use session actions.'
                return
            if action == 'clear':
                self.world.clear()
            else:
                width = self.app.screen.get_width()
                for i in range(8):
                    self.world.spawn(70+i*(width-140)/7, 100+(i % 3)*18)
            self.status = 'Shapes cleared.' if action == 'clear' else 'Spawned eight shapes.'
        elif action == 'reset':
            self.settings = dict(DEFAULTS)
            self.save()
            self.configure_cpe()
        elif action in ('flasher', 'root-guide'):
            import webbrowser
            webbrowser.open(ROOT_GUIDE_URL if action == 'root-guide' else FLASHER_URL)

    def text(self, screen, value, pos, size=19, color=TEXT, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont('segoeui', size, bold=bold)
        image = self.fonts[key].render(str(value), True, color)
        screen.blit(image, pos)

    def draw(self):
        self.configure_cpe()
        screen = self.app.screen
        width, height = screen.get_size()
        badge = pygame.Rect(width-236, 76, 220, 34)
        pygame.draw.rect(screen, BG, badge, border_radius=9)
        self.text(screen, 'NUTTYMOD', (badge.x+12, badge.y+8), 14, ACCENT, True)
        self.text(screen, 'F8  MENU', (badge.right-78, badge.y+8), 13, MUTED)
        if self.in_simulation:
            lines = []
            if self.settings['fps']:
                fps = self.app.clock.get_fps()
                lines.append(f'{fps:.0f} FPS  /  {1000/fps:.1f} ms' if fps > 0 else 'FPS  /  warming up')
            if self.settings['stats']:
                mode = 'MULTIPLAYER' if self.multiplayer else 'SOLO'
                lines.append(f'{self.shape_count} SHAPES  /  {mode}')
                active = [] if self.multiplayer else [label for key, label in (
                    ('low_gravity', 'LOW GRAVITY'), ('slow_motion', '0.5x SPEED')) if self.settings[key]]
                if active:
                    lines.append('  /  '.join(active))
                if self.optimizer_active:
                    lines.append('OPTIMIZER  /  FAST CPE')
            if lines:
                rect = pygame.Rect(width-236, 116, 220, len(lines)*24+14)
                pygame.draw.rect(screen, BG, rect, border_radius=9)
                for i, line in enumerate(lines):
                    self.text(screen, line, (rect.x+12, rect.y+7+i*24), 13)
            if self.settings['crosshair'] and not self.open:
                x, y = pygame.mouse.get_pos()
                for color, stroke in (((5, 12, 18), 4), (ACCENT, 2)):
                    pygame.draw.line(screen, color, (x-9, y), (x-3, y), stroke)
                    pygame.draw.line(screen, color, (x+3, y), (x+9, y), stroke)
                    pygame.draw.line(screen, color, (x, y-9), (x, y-3), stroke)
                    pygame.draw.line(screen, color, (x, y+3), (x, y+9), stroke)
            if self.settings['keys']:
                for i, (key, label) in enumerate(((pygame.K_c, 'C'), (pygame.K_e, 'E'),
                                                (pygame.K_p, 'P'), (pygame.K_SPACE, 'SPACE'))):
                    rect = pygame.Rect(16+i*61, height-108, 55, 34)
                    pygame.draw.rect(screen, ACCENT if key in self.held else BG, rect, border_radius=7)
                    self.text(screen, label, (rect.x+9, rect.y+9), 13, BG if key in self.held else TEXT)
        if self.open:
            self.draw_menu(screen)

    def draw_menu(self, screen):
        panel, x, y, width = self.layout()
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((3, 8, 14, 170))
        screen.blit(shade, (0, 0))
        pygame.draw.rect(screen, BG, panel, border_radius=18)
        pygame.draw.rect(screen, LINE, panel, 1, border_radius=18)
        pygame.draw.line(screen, LINE, (panel.x+18, panel.y+90), (panel.right-18, panel.y+90))
        pygame.draw.line(screen, LINE, (panel.x+181, panel.y+108), (panel.x+181, panel.bottom-60))
        self.text(screen, 'NUTTYMOD', (panel.x+26, panel.y+22), 29, ACCENT, True)
        self.text(screen, 'CLIENT  /  '+VERSION, (panel.x+27, panel.y+60), 13, MUTED)
        self.text(screen, self.tab.upper(), (x, panel.y+60), 13, MUTED, True)
        controls = self.controls()
        mouse = pygame.mouse.get_pos()
        labels = {
            'fps': ('FPS counter', 'Frame rate and average frame time.'),
            'stats': ('Session statistics', 'Shape count, mode and active physics settings.'),
            'crosshair': ('Precision crosshair', 'A mint crosshair follows your pointer.'),
            'keys': ('Keystrokes', 'Show C, E, P and Space while playing.'),
            'neon': ('Nutty palette', 'Mint, blue, lavender and pink shapes in solo play.'),
            'low_gravity': ('Low gravity', 'One-quarter gravity in solo play.'),
            'slow_motion': ('Slow motion', 'Run solo physics at half speed.'),
            'cpe_enabled': ('Custom CPE settings', 'Apply basic and advanced tuning to solo sessions.'),
            'cpe_particles': ('CPE particles', 'Turn IPE effects on or off while tuning is enabled.'),
            'optimizer': ('NuttyMod Optimizer', 'Force Fast CPE. Requires NuttyMod Root + Root Mode.'),
        }
        cycles = {
            'cpe_preset': ('CPE preset', 'Click to cycle Balanced, Quality and Custom.'),
            'cpe_iterations': ('Solver iterations', 'Click to cycle 4, 8, 12, 20 and 30.'),
            'cpe_particle_limit': ('Particle budget', 'Click to cycle 0, 200, 800, 1600 and 4000.'),
            'cpe_step_hz': ('Simulation rate', 'Click to cycle 60, 120 and 240 Hz.'),
        }
        for rect, action in controls:
            if action == 'close':
                pygame.draw.rect(screen, CARD, rect, border_radius=7)
                self.text(screen, 'x', (rect.x+10, rect.y+3), 20)
            elif action.startswith('tab:'):
                selected = action[4:] == self.tab
                pygame.draw.rect(screen, ACCENT if selected else CARD, rect, border_radius=8)
                self.text(screen, action[4:], (rect.x+14, rect.y+10), 17, BG if selected else TEXT, selected)
            elif action in labels:
                disabled = ((self.tab in ('Physics', 'CPE Basic', 'CPE Advanced', 'Root') and self.multiplayer)
                            or (action == 'optimizer' and not self.root_ready()))
                pygame.draw.rect(screen, (28, 42, 53) if rect.collidepoint(mouse) else CARD, rect, border_radius=9)
                label, detail = labels[action]
                self.text(screen, label, (rect.x+14, rect.y+7), 18, MUTED if disabled else TEXT)
                self.text(screen, detail, (rect.x+14, rect.y+32), 12, MUTED)
                toggle = pygame.Rect(rect.right-56, rect.y+15, 40, 23)
                enabled = self.settings[action] and not disabled
                pygame.draw.rect(screen, ACCENT if enabled else LINE, toggle, border_radius=12)
                pygame.draw.circle(screen, BG if enabled else MUTED, (toggle.x+(28 if enabled else 12), toggle.centery), 8)
            elif action.startswith('cycle:'):
                key = action[6:]
                label, detail = cycles[key]
                pygame.draw.rect(screen, CARD, rect, border_radius=9)
                self.text(screen, label, (rect.x+14, rect.y+7), 18, MUTED if self.multiplayer else TEXT)
                self.text(screen, detail, (rect.x+14, rect.y+32), 12, MUTED)
                self.text(screen, str(self.settings[key]), (rect.right-100, rect.y+10), 19, ACCENT)
            else:
                available = action not in ('rain', 'clear') or (
                    self.in_simulation and not self.multiplayer and self.world is not None)
                if action == 'reset-cpe' and self.multiplayer:
                    available = False
                pygame.draw.rect(screen, CARD, rect, border_radius=8)
                pygame.draw.rect(screen, LINE, rect, 1, border_radius=8)
                label = {'rain': 'Spawn 8 shapes', 'clear': 'Clear shapes',
                         'reset': 'Reset client settings', 'flasher': 'Open CPE Flasher Tool website',
                         'reset-cpe': 'Reset CPE to game defaults', 'root-guide': 'Open Root setup guide'}[action]
                self.text(screen, label, (rect.x+14, rect.y+12), 16, ACCENT if available else MUTED)
        if self.tab == 'Physics':
            self.text(screen, 'Physics controls and session actions work in solo play.', (x, y+274), 13, MUTED)
            self.text(screen, 'Multiplayer uses the original game physics.', (x, y+298), 13, MUTED)
        elif self.tab in ('CPE Basic', 'CPE Advanced'):
            note = 'Optimizer takes priority: Fast CPE / 120 Hz / up to 800 particles.' if self.optimizer_active else 'Solo tuning. Game defaults apply when custom settings are off.'
            self.text(screen, note, (x, y+272), 12, MUTED)
            state = next((item for item in self.engine_states if item.engine is getattr(self.world, 'cpe', None)), None)
            if state and state.supported:
                step = getattr(state.engine, '_fixed_step', None)
                hz = f'{1/step:.0f} Hz' if step else 'native rate'
                live = f'LIVE: {state.space.iterations} iterations / {hz} / {state.particles.max_particles} particles'
            else:
                live = 'Start solo play to inspect the active CPE engine.'
            self.text(screen, live, (x, y+298), 13, ACCENT)
            self.text(screen, 'Advanced changes select the Custom preset.', (x, y+324), 12, MUTED)
        elif self.tab == 'Root':
            root = getattr(self.app, 'nuttymod_root_enabled', False) is True
            mode = getattr(self.app, 'root_mode_enabled', False) is True
            lines = (
                'NuttyMod Root: '+('ACTIVE' if root else 'REQUIRED'),
                'Root Mode: '+('ACTIVE' if mode else 'REQUIRED'),
                'Optimizer: '+self.optimizer_status(),
                'Optional, off by default. Both Root components must be active.',
                'Forces native Fast CPE where supported; older engines use',
                'a compatibility preset with less solver work and IPE effects.',
                '120 Hz physics. Up to 800 particles. Restores settings on exit.',
                'Fewer effects; stacks and collisions may be less precise.',
            )
            for i, line in enumerate(lines):
                self.text(screen, line, (x, y+78+i*24), 13, ACCENT if i < 3 else MUTED)
        elif self.tab == 'About':
            for i, (line, size, color) in enumerate((
                ('Your Cube. Your client.', 25, TEXT),
                ('NuttyMod Client for The Cube Beta.', 16, MUTED),
                ('Install through CPE Flasher Tool.', 16, TEXT),
                ('nuttyinc578.github.io/CPE-flashing-tool/', 15, ACCENT),
                ('F8 / Esc  Close     Tab  Next page', 15, MUTED),
            )):
                self.text(screen, line, (x, y+i*36), size, color)
        pygame.draw.line(screen, LINE, (panel.x+18, panel.bottom-53), (panel.right-18, panel.bottom-53))
        self.text(screen, self.status, (panel.x+26, panel.bottom-36), 13, MUTED)
        self.text(screen, 'F8 / ESC', (panel.right-88, panel.bottom-36), 12, ACCENT)


def on_load(app, userdata):
    """Called by the flasher only after the user has unlocked CPELoader."""
    if getattr(app, 'nuttymod_client_enabled', False):
        return
    app.cpeloader.require_flash()
    root = Path(globals().get('game_root', Path.cwd()))
    NuttyModClient(app, root).install()
