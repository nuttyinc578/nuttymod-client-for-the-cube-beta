"""NuttyMod Client: an explicit CubeBeta/1 startup hook for CPE Flasher Tool."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import MethodType

import pygame

VERSION = '1.0.0'
FLASHER_URL = 'https://nuttyinc578.github.io/CPE-flashing-tool/'
DEFAULTS = {
    'fps': True, 'stats': True, 'crosshair': False, 'keys': False,
    'neon': True, 'low_gravity': False, 'slow_motion': False,
}
PALETTE = ((111, 245, 193), (118, 195, 255), (185, 157, 255), (255, 178, 211))
BG, CARD, LINE = (13, 20, 29), (22, 32, 43), (42, 57, 70)
TEXT, MUTED, ACCENT = (236, 245, 246), (143, 163, 176), PALETTE[0]


class NuttyModClient:
    def __init__(self, app, root):
        self.app = app
        self.path = Path(root)/'userdata'/'nuttymod-client'/'settings.json'
        self.settings = dict(DEFAULTS)
        try:
            if self.path.stat().st_size <= 65536:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data.get('schema') == 1:
                    self.settings.update({key: data[key] for key in DEFAULTS if type(data.get(key)) is bool})
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

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'schema': 1, **self.settings}, indent=2)+'\n', encoding='utf-8')
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
                        tabs = ('Display', 'Physics', 'About')
                        self.tab = tabs[(tabs.index(self.tab)+1) % len(tabs)]
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
                     for i, tab in enumerate(('Display', 'Physics', 'About'))]
        names = ('fps', 'stats', 'crosshair', 'keys', 'neon') if self.tab == 'Display' else (
            ('low_gravity', 'slow_motion') if self.tab == 'Physics' else ())
        controls += [(pygame.Rect(x, y+i*64, width, 54), name) for i, name in enumerate(names)]
        if self.tab == 'Physics':
            controls += [(pygame.Rect(x, y+150+i*54, width, 44), action)
                         for i, action in enumerate(('rain', 'clear'))]
        if self.tab == 'About':
            controls += [(pygame.Rect(x, y+202+i*54, width, 44), action)
                         for i, action in enumerate(('flasher', 'reset'))]
        return controls

    def activate(self, action):
        if action == 'close':
            self.open = False
        elif action.startswith('tab:'):
            self.tab = action[4:]
        elif action in DEFAULTS:
            if self.tab == 'Physics' and self.multiplayer:
                self.status = 'Physics controls are available in solo play.'
                return
            self.settings[action] = not self.settings[action]
            self.save()
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
        elif action == 'flasher':
            import webbrowser
            webbrowser.open(FLASHER_URL)

    def text(self, screen, value, pos, size=19, color=TEXT, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont('segoeui', size, bold=bold)
        image = self.fonts[key].render(str(value), True, color)
        screen.blit(image, pos)

    def draw(self):
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
                disabled = self.tab == 'Physics' and self.multiplayer
                pygame.draw.rect(screen, (28, 42, 53) if rect.collidepoint(mouse) else CARD, rect, border_radius=9)
                label, detail = labels[action]
                self.text(screen, label, (rect.x+14, rect.y+7), 18, MUTED if disabled else TEXT)
                self.text(screen, detail, (rect.x+14, rect.y+32), 12, MUTED)
                toggle = pygame.Rect(rect.right-56, rect.y+15, 40, 23)
                enabled = self.settings[action] and not disabled
                pygame.draw.rect(screen, ACCENT if enabled else LINE, toggle, border_radius=12)
                pygame.draw.circle(screen, BG if enabled else MUTED, (toggle.x+(28 if enabled else 12), toggle.centery), 8)
            else:
                available = action not in ('rain', 'clear') or (
                    self.in_simulation and not self.multiplayer and self.world is not None)
                pygame.draw.rect(screen, CARD, rect, border_radius=8)
                pygame.draw.rect(screen, LINE, rect, 1, border_radius=8)
                label = {'rain': 'Spawn 8 shapes', 'clear': 'Clear shapes',
                         'reset': 'Reset client settings', 'flasher': 'Open CPE Flasher Tool website'}[action]
                self.text(screen, label, (rect.x+14, rect.y+12), 16, ACCENT if available else MUTED)
        if self.tab == 'Physics':
            self.text(screen, 'Physics controls and session actions work in solo play.', (x, y+274), 13, MUTED)
            self.text(screen, 'Multiplayer uses the original game physics.', (x, y+298), 13, MUTED)
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
