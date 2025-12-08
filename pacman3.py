# pacman_levels_fixed.py
import pygame
import math
import sys
import random

# ---------- إعدادات عامة ----------
WIDTH, HEIGHT = 800, 600
FPS = 60

# ألوان
BG_COLOR = (10, 10, 30)
PACMAN_COLOR = (255, 205, 0)
EYE_COLOR = (0, 0, 0)
PELLET_COLOR = (255, 200, 200)
HUD_COLOR = (230, 230, 230)
GHOST_COLORS = [(255, 0, 0), (255, 128, 255), (0, 255, 255), (255, 165, 0)]

# باك-مان افتراضيات
start_pos = [WIDTH // 4, HEIGHT // 2]
radius = 28
base_speed = 3.2

# فم باك-مان
mouth_open = 0.0
mouth_target = 0.0
mouth_speed_param = 6.0
mouth_max_angle = 35

# إعداد Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pacman")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
large_font = pygame.font.SysFont(None, 56)

# ---------- عناصر المستوى ----------
def make_pellets(grid_w=20, grid_h=15, margin=60):
    pellets = []
    cell_w = (WIDTH - margin * 2) / grid_w
    cell_h = (HEIGHT - margin * 2) / grid_h
    for i in range(grid_w):
        for j in range(grid_h):
            x = int(margin + i * cell_w + cell_w / 2)
            y = int(margin + j * cell_h + cell_h / 2)
            pellets.append([x, y, 6])
    return pellets

# ---------- كائن الأشباح ----------
class Ghost:
    def __init__(self, x, y, color, speed):
        self.pos = [float(x), float(y)]
        self.color = color
        self.speed = float(speed)
        vx = random.uniform(-1.0, 1.0)
        vy = random.uniform(-1.0, 1.0)
        vlen = math.hypot(vx, vy) + 1e-6
        self.dir = [vx / vlen, vy / vlen]
        self.frightened = False
        self.radius = 22

    def update(self, pac_pos, dt, level):
        chase_factor = 0.55 + 0.05 * level
        if random.random() < 0.02:
            self.dir = [random.uniform(-1, 1), random.uniform(-1, 1)]

        to_pac = [pac_pos[0] - self.pos[0], pac_pos[1] - self.pos[1]]
        dist = math.hypot(to_pac[0], to_pac[1]) + 1e-6
        to_pac_norm = [to_pac[0] / dist, to_pac[1] / dist]

        self.dir[0] = (1 - chase_factor) * self.dir[0] + chase_factor * to_pac_norm[0]
        self.dir[1] = (1 - chase_factor) * self.dir[1] + chase_factor * to_pac_norm[1]

        dlen = math.hypot(self.dir[0], self.dir[1]) + 1e-6
        self.dir[0] /= dlen
        self.dir[1] /= dlen

        self.pos[0] += self.dir[0] * self.speed * dt
        self.pos[1] += self.dir[1] * self.speed * dt

        if self.pos[0] - self.radius < 0:
            self.pos[0] = self.radius
            self.dir[0] *= -1
        if self.pos[0] + self.radius > WIDTH:
            self.pos[0] = WIDTH - self.radius
            self.dir[0] *= -1
        if self.pos[1] - self.radius < 0:
            self.pos[1] = self.radius
            self.dir[1] *= -1
        if self.pos[1] + self.radius > HEIGHT:
            self.pos[1] = HEIGHT - self.radius
            self.dir[1] *= -1

    def draw(self, surface):
        x, y = int(self.pos[0]), int(self.pos[1])
        pygame.draw.circle(surface, self.color, (x, y), self.radius)
        eye_offset = 10
        pygame.draw.circle(surface, (255, 255, 255), (x - eye_offset, y - 6), 6)
        pygame.draw.circle(surface, (255, 255, 255), (x + eye_offset, y - 6), 6)
        pygame.draw.circle(surface, (0, 0, 0), (x - eye_offset, y - 6), 3)
        pygame.draw.circle(surface, (0, 0, 0), (x + eye_offset, y - 6), 3)

# ---------- حالة اللعبة ----------
class GameState:
    def __init__(self):
        self.level = 1
        self.score = 0
        self.lives = 3
        self.pac_pos = [float(start_pos[0]), float(start_pos[1])]
        self.vel = [base_speed, 0.0]
        self.pellets = make_pellets()
        self.ghosts = []
        self.respawn_timer = 0.0
        self.invulnerable_time = 0.0
        self.spawn_ghosts_for_level()

    def spawn_ghosts_for_level(self):
        self.ghosts.clear()
        num_ghosts = min(4, 1 + (self.level - 1))
        base_ghost_speed = 70 + 8 * (self.level - 1)
        for i in range(num_ghosts):
            tries = 0
            while True:
                x = random.randint(100, WIDTH - 100)
                y = random.randint(80, HEIGHT - 80)
                if math.hypot(x - self.pac_pos[0], y - self.pac_pos[1]) > 140:
                    break
                tries += 1
                if tries > 200:
                    break
            color = GHOST_COLORS[i % len(GHOST_COLORS)]
            g = Ghost(x, y, color, base_ghost_speed)
            self.ghosts.append(g)

    def reset_level(self):
        self.pellets = make_pellets()
        self.pac_pos = [float(start_pos[0]), float(start_pos[1])]
        self.vel = [base_speed, 0.0]
        self.invulnerable_time = 0.8
        self.spawn_ghosts_for_level()

# ---------- رسم باك-مان ----------
def draw_pacman(surface, center, radius, direction_vector, mouth_angle_deg, mouth_open_ratio):
    cx, cy = center
    dx, dy = direction_vector
    if dx == 0 and dy == 0:
        dx = 1
    angle = math.degrees(math.atan2(-dy, dx))
    half_angle = mouth_angle_deg * mouth_open_ratio
    a1 = math.radians(angle + half_angle)
    a2 = math.radians(angle - half_angle)

    pygame.draw.circle(surface, PACMAN_COLOR, (int(cx), int(cy)), radius)

    mouth_points = [(cx, cy)]
    steps = 12
    for t in range(steps + 1):
        theta = a1 + (a2 - a1) * (t / steps)
        mouth_points.append((cx + radius * math.cos(theta), cy - radius * math.sin(theta)))

    try:
        pygame.draw.polygon(surface, (0, 0, 0, 0), mouth_points)
    except TypeError:
        pygame.draw.polygon(surface, BG_COLOR, mouth_points)

    eye_offset_angle = math.radians(angle - 25)
    eye_dist = radius * 0.45
    eye_x = cx + eye_dist * math.cos(eye_offset_angle)
    eye_y = cy - eye_dist * math.sin(eye_offset_angle)
    eye_radius = max(3, int(radius * 0.12))
    pygame.draw.circle(surface, EYE_COLOR, (int(eye_x), int(eye_y)), eye_radius)

# ---------- اللعبة الرئيسية ----------
def main():
    gs = GameState()
    running = True
    global mouth_open, mouth_target, mouth_speed_param

    show_level_message = True
    level_msg_timer = 1.2

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        vx, vy = 0.0, 0.0
        speed = base_speed + 0.12 * (gs.level - 1)
        if keys[pygame.K_LEFT]:
            vx = -speed
        elif keys[pygame.K_RIGHT]:
            vx = speed
        if keys[pygame.K_UP]:
            vy = -speed
        elif keys[pygame.K_DOWN]:
            vy = speed
        if vx != 0 or vy != 0:
            gs.vel = [vx, vy]

        t = pygame.time.get_ticks() / 1000.0
        mouth_target = (math.sin(t * math.pi * mouth_speed_param) + 1) / 2
        mouth_open += (mouth_target - mouth_open) * min(1.0, 8.0 * dt)
        current_mouth_angle = mouth_open * mouth_max_angle

        gs.pac_pos[0] += gs.vel[0] * dt * 60.0
        gs.pac_pos[1] += gs.vel[1] * dt * 60.0

        if gs.pac_pos[0] - radius < 0:
            gs.pac_pos[0] = radius
        if gs.pac_pos[0] + radius > WIDTH:
            gs.pac_pos[0] = WIDTH - radius
        if gs.pac_pos[1] - radius < 0:
            gs.pac_pos[1] = radius
        if gs.pac_pos[1] + radius > HEIGHT:
            gs.pac_pos[1] = HEIGHT - radius

        for g in gs.ghosts:
            g.update(gs.pac_pos, dt, gs.level)

        remaining = []
        for p in gs.pellets:
            if math.hypot(p[0] - gs.pac_pos[0], p[1] - gs.pac_pos[1]) <= (p[2] + radius * 0.6):
                gs.score += 10
            else:
                remaining.append(p)
        gs.pellets = remaining

        if gs.invulnerable_time > 0:
            gs.invulnerable_time -= dt

        if gs.respawn_timer > 0:
            gs.respawn_timer -= dt
            if gs.respawn_timer <= 0:
                gs.pac_pos = [float(start_pos[0]), float(start_pos[1])]
                gs.invulnerable_time = 0.6
        else:
            for g in gs.ghosts:
                if math.hypot(g.pos[0] - gs.pac_pos[0], g.pos[1] - gs.pac_pos[1]) < (g.radius + radius - 6):
                    if gs.invulnerable_time <= 0:
                        gs.lives -= 1
                        gs.invulnerable_time = 1.0
                        gs.respawn_timer = 1.2
                        if gs.lives <= 0:
                            restart = game_over_screen(gs)
                            if not restart:
                                pygame.quit()
                                sys.exit()
                            else:
                                gs = GameState()
                                show_level_message = True
                                level_msg_timer = 1.2
                                break
                    break

        if not gs.pellets and gs.respawn_timer <= 0:
            gs.level += 1
            gs.score += 500
            mouth_speed_param += 0.6
            gs.reset_level()
            show_level_message = True
            level_msg_timer = 1.4

        screen.fill(BG_COLOR)

        for p in gs.pellets:
            pygame.draw.circle(screen, PELLET_COLOR, (int(p[0]), int(p[1])), p[2])

        for g in gs.ghosts:
            g.draw(screen)

        flash = 1.0
        if gs.invulnerable_time > 0:
            flash = 0.4 + 0.6 * (0.5 * (1 + math.sin(pygame.time.get_ticks() / 100.0)))
        dir_vec = gs.vel if (gs.vel[0] != 0 or gs.vel[1] != 0) else (1, 0)
        pac_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        draw_pacman(pac_surface, (radius + 2, radius + 2), radius, dir_vec, current_mouth_angle, mouth_open)
        pac_surface.set_alpha(int(255 * flash))
        screen.blit(pac_surface, (int(gs.pac_pos[0] - radius - 2), int(gs.pac_pos[1] - radius - 2)))

        hud = f"Score: {gs.score}    Lives: {gs.lives}    Level: {gs.level}    Pellets: {len(gs.pellets)}"
        text = font.render(hud, True, HUD_COLOR)
        screen.blit(text, (12, 10))

        if show_level_message:
            level_text = large_font.render(f"Level {gs.level}", True, HUD_COLOR)
            rect = level_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(level_text, rect)
            level_msg_timer -= dt
            if level_msg_timer <= 0:
                show_level_message = False

        pygame.display.flip()

    pygame.quit()
    sys.exit()

def game_over_screen(gs):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                elif event.key == pygame.K_ESCAPE:
                    return False

        screen.fill((5, 5, 30))
        over_text = large_font.render("GAME OVER", True, (220, 50, 50))
        score_text = font.render(f"Final Score: {gs.score}", True, HUD_COLOR)
        instruct = font.render("Press R to Restart or ESC to Quit", True, HUD_COLOR)

        screen.blit(over_text, over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50)))
        screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 6)))
        screen.blit(instruct, instruct.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 46)))
        pygame.display.flip()
        clock.tick(10)

if __name__ == "__main__":
    main()
