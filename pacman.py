# pacman_levels.py
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

# فم باك-مان (لسلاسة الحركة نستخدم interpolation)
mouth_open = 0.0          # من 0 إلى 1
mouth_target = 0.0
mouth_speed_param = 6.0   # تردد الاهتزاز (يمكن زيادته مع المستويات)
mouth_max_angle = 35      # درجات - نصف زاوية الفم القصوى

# إعداد Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pac-Man - مستويات")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
large_font = pygame.font.SysFont(None, 56)

# أصوات بسيطة (يعمل بدون ملفات - نستخدم beeps قصيرة إن أردت، لكن هنا نخليها None لتجنب مشاكل)
eat_sound = None
hurt_sound = None
level_up_sound = None

# ---------- عناصر المستوى: حبات (pellets) ----------
def make_pellets(grid_w=20, grid_h=15, margin=60):
    """توليد نقاط موزعة في شبكة داخل النافذة (تجنب الحواف)"""
    pellets = []
    cell_w = (WIDTH - margin * 2) / grid_w
    cell_h = (HEIGHT - margin * 2) / grid_h
    for i in range(grid_w):
        for j in range(grid_h):
            x = int(margin + i * cell_w + cell_w / 2)
            y = int(margin + j * cell_h + cell_h / 2)
            # مسافة صغيرة من مركز النافذة أو نقاط عشوائية يمكن أن تُزال؛ هنا نحتفظ بكلها
            pellets.append([x, y, 6])  # [x,y,radius]
    return pellets

# ---------- كائن الأشباح ----------
class Ghost:
    def init(self, x, y, color, speed):
        self.pos = [x, y]
        self.color = color
        self.speed = speed
        self.dir = [random.choice([-1,1]), random.choice([-1,1])]
        self.frightened = False  # لاحقاً يمكن استخدامه
        self.radius = 22

    def update(self, pac_pos, dt, level):
        # سلوك بسيط: خليط بين الاقتراب العشوائي والتتبع:
        chase_factor = 0.55 + 0.05 * level  # مع ازدياد المستوى، تصبح الأشباح أكثر متابعة
        if random.random() < 0.02:  # تغيير عشوائي بسيط في الاتجاه
            self.dir = [random.uniform(-1, 1), random.uniform(-1, 1)]

        # اتجاه نحو باك-مان
        to_pac = [pac_pos[0] - self.pos[0], pac_pos[1] - self.pos[1]]
        dist = math.hypot(to_pac[0], to_pac[1]) + 1e-6
        to_pac_norm = [to_pac[0] / dist, to_pac[1] / dist]

        # مزيج من الاتجاه الحالي واتجاه المطاردة
        self.dir[0] = (1 - chase_factor) * self.dir[0] + chase_factor * to_pac_norm[0]
        self.dir[1] = (1 - chase_factor) * self.dir[1] + chase_factor * to_pac_norm[1]

        # Normalize
        dlen = math.hypot(self.dir[0], self.dir[1]) + 1e-6
        self.dir[0] /= dlen
        self.dir[1] /= dlen

        # تحديث الموضع مع الارتداد عن الحواف
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
        # جسم أشباح بسيط: نصف دائرة ثم مستطيل صغير
        x, y = int(self.pos[0]), int(self.pos[1])
        pygame.draw.circle(surface, self.color, (x, y), self.radius)
        # "عيون" بيضاء + بؤبؤ
        eye_offset = 10
        pygame.draw.circle(surface, (255,255,255), (x - eye_offset, y - 6), 6)
        pygame.draw.circle(surface, (255,255,255), (x + eye_offset, y - 6), 6)
        pygame.draw.circle(surface, (0,0,0), (x - eye_offset, y - 6), 3)
        pygame.draw.circle(surface, (0,0,0), (x + eye_offset, y - 6), 3)

# ---------- حالة اللعبة ----------
class GameState:
    def init(self):
        self.level = 1
        self.score = 0
        self.lives = 3
        self.pac_pos = start_pos.copy()
        self.vel = [base_speed, 0]
        self.pellets = make_pellets()
        self.ghosts = []
        self.spawn_ghosts_for_level()
        self.respawn_timer = 0.0
        self.invulnerable_time = 0.0

    def spawn_ghosts_for_level(self):
        self.ghosts.clear()
        num_ghosts = min(4, 1 + (self.level - 1) // 1)  # زياد تدريجى
        base_ghost_speed = 70 + 8 * (self.level - 1)  # سرعة بكسل/ثانية
        for i in range(num_ghosts):
            # توليد في مواقع عشوائية بعيدة عن باك-مان
            while True:
                x = random.randint(100, WIDTH - 100)
                y = random.randint(80, HEIGHT - 80)
                if math.hypot(x - self.pac_pos[0], y - self.pac_pos[1]) > 140:
                    break
            color = GHOST_COLORS[i % len(GHOST_COLORS)]
            g = Ghost(x, y, color, base_ghost_speed)
            self.ghosts.append(g)

    def reset_level(self):
        self.pellets = make_pellets()
        self.pac_pos = start_pos.copy()
        self.vel = [base_speed, 0]
        self.invulnerable_time = 0.8  # فترة قصيرة بعد الهروب / الموت
        self.spawn_ghosts_for_level()

# ---------- رسم باك-مان محسّن ----------
def draw_pacman(surface, center, radius, direction_vector, mouth_angle_deg, mouth_open_ratio):
    cx, cy = center
    dx, dy = direction_vector
    if dx == 0 and dy == 0:
        dx = 1
    angle = math.degrees(math.atan2(-dy, dx))
    half_angle = mouth_angle_deg * mouth_open_ratio
    a1 = math.radians(angle + half_angle)
    a2 = math.radians(angle - half_angle)

    # نقاط الفم على محيط الدائرة
    p1 = (cx + radius * math.cos(a1), cy - radius * math.sin(a1))
    p2 = (cx + radius * math.cos(a2), cy - radius * math.sin(a2))

    # نرسم شكل دائري باستخدام arc + ملء للحصول على مظهر أنعم:
    # - سنرسم القطاع (عن طريق polygon من عدة نقاط على القوس) لعمل تأثير الفم
    # رسم الجسم
    pygame.draw.circle(surface, PACMAN_COLOR, (int(cx), int(cy)), radius)

    # نُغطي الفم باستخدام مثلث تقريبي لكن مع حواف أكثر نعومة عبر polygon مكون من نقاط متعددة
    mouth_points = [(cx, cy)]
    steps = 10
    for t in range(steps + 1):
        theta = a1 + (a2 - a1) * (t / steps)
        mouth_points.append((cx + radius * math.cos(theta), cy - radius * math.sin(theta)))
    pygame.draw.polygon(surface, BG_COLOR, mouth_points)

    # العين (تحرك طفيف حسب الاتجاه)
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

    # مؤقت لتأخير بداية كل مستوى (لعرض رسالة)
    show_level_message = True
    level_msg_timer = 1.2

    while running:
        dt = clock.tick(FPS) / 1000.0  # ثواني
        # الأحداث
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # إدخال مفاتيح الحركة
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

# تحديث الفم: target يعتمد على تردد الفم وسرعة الفم، نجعل الفتح مرتبطاً بالسرعة الحالية لتحسين الإحساس "بالمضغ"
        t = pygame.time.get_ticks() / 1000.0
        mouth_target = (math.sin(t * math.pi * mouth_speed_param) + 1) / 2
        # تجانس نحو الهدف (lerp) للحصول على حركة أنعم
        mouth_open += (mouth_target - mouth_open) * min(1.0, 8.0 * dt)
        current_mouth_angle = mouth_open * mouth_max_angle

        # نقل باك-مان (مع حدود الشاشة)
        gs.pac_pos[0] += gs.vel[0]
        gs.pac_pos[1] += gs.vel[1]

        if gs.pac_pos[0] - radius < 0:
            gs.pac_pos[0] = radius
        if gs.pac_pos[0] + radius > WIDTH:
            gs.pac_pos[0] = WIDTH - radius
        if gs.pac_pos[1] - radius < 0:
            gs.pac_pos[1] = radius
        if gs.pac_pos[1] + radius > HEIGHT:
            gs.pac_pos[1] = HEIGHT - radius

        # تحديث الأشباح
        for g in gs.ghosts:
            # سرعة في البيكسل/ثانية مبدوءة في Ghost, نضرب dt
            g.update(gs.pac_pos, dt, gs.level)

        # التحقق من التصادم مع الحبات (pellets)
        remaining = []
        for p in gs.pellets:
            if math.hypot(p[0] - gs.pac_pos[0], p[1] - gs.pac_pos[1]) <= (p[2] + radius * 0.6):
                gs.score += 10
                # يمكن تشغيل صوت هنا لو أردت
            else:
                remaining.append(p)
        gs.pellets = remaining

        # تحقق تصادم مع أشباح (مع فترة لا يمكن التصادم فيها بعد الموت)
        if gs.invulnerable_time > 0:
            gs.invulnerable_time -= dt

        if gs.respawn_timer > 0:
            gs.respawn_timer -= dt
            if gs.respawn_timer <= 0:
                # بعد انتهاء مؤقت الإحياء نعيد الوضع الطبيعي
                gs.pac_pos = start_pos.copy()
                gs.invulnerable_time = 0.6
        else:
            for g in gs.ghosts:
                if math.hypot(g.pos[0] - gs.pac_pos[0], g.pos[1] - gs.pac_pos[1]) < (g.radius + radius - 6):
                    # اصطدام
                    if gs.invulnerable_time <= 0:
                        gs.lives -= 1
                        gs.invulnerable_time = 1.0
                        gs.respawn_timer = 1.2
                        # تفقد/إعادة تعيين
                        if hurt_sound:
                            hurt_sound.play()
                        if gs.lives <= 0:
                            # Game over
                            running = game_over_screen(gs)
                            # عند العودة من شاشة النهاية، إما يختار اللاعب إعادة التشغيل أو الخروج
                            if not running:
                                pygame.quit()
                                sys.exit()
                            else:
                                # إذا اختار إعادة التشغيل، إعادة تهيئة الحالة
                                gs = GameState()
                                show_level_message = True
                                level_msg_timer = 1.2
                                break
                        break

        # انتهت الحبات -> مستوى جديد
        if not gs.pellets and gs.respawn_timer <= 0:
            gs.level += 1
            gs.score += 500  # مكافأة مستوى
            # زيادة تردد الفم وقليل من الصعوبة
            mouth_speed_param += 0.6
            # توليد حبات جديدة، إعادة أماكن الأشباح
            gs.reset_level()
            show_level_message = True
            level_msg_timer = 1.4
            if level_up_sound:
                level_up_sound.play()

        # رسم
        screen.fill(BG_COLOR)

        # رسم الحبات
        for p in gs.pellets:
            pygame.draw.circle(screen, PELLET_COLOR, (int(p[0]), int(p[1])), p[2])

        # رسم الأشباح
        for g in gs.ghosts:
            g.draw(screen)

# رسم باك-مان (مع وميض بسيط أثناء عدم قابلية التصادم)
        flash = 1.0
        if gs.invulnerable_time > 0:
            # وميض بمعدل سريع
            flash = 0.4 + 0.6 * (0.5 * (1 + math.sin(pygame.time.get_ticks() / 100.0)))
        dir_vec = gs.vel if (gs.vel[0] != 0 or gs.vel[1] != 0) else (1, 0)
        pac_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        # draw_pacman يستخدم إحداثيات مركزية لذلك نمرر مركز داخل السطح الصغير
        draw_pacman(pac_surface, (radius+2, radius+2), radius, dir_vec, current_mouth_angle, mouth_open)
        # تطبيق وميض عن طريق تغيير ألفا
        pac_surface.set_alpha(int(255 * flash))
        screen.blit(pac_surface, (gs.pac_pos[0] - radius - 2, gs.pac_pos[1] - radius - 2))

        # HUD
        hud = f"Score: {gs.score}    Lives: {gs.lives}    Level: {gs.level}    Pellets: {len(gs.pellets)}"
        text = font.render(hud, True, HUD_COLOR)
        screen.blit(text, (12, 10))

        # رسالة مستوى جديد
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
    """عرض شاشة النهاية؛ ترجع True إذا اللاعب يريد إعادة تشغيل، False للخروج"""
    waiting = True
    choice = False
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                elif event.key == pygame.K_ESCAPE:
                    return False

        screen.fill((5, 5, 30))
        over_text = large_font.render("GAME OVER", True, (220,50,50))
        score_text = font.render(f"Final Score: {gs.score}", True, HUD_COLOR)
        instruct = font.render("Press R to Restart or ESC to Quit", True, HUD_COLOR)

        screen.blit(over_text, over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
        screen.blit(score_text, score_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 6)))
        screen.blit(instruct, instruct.get_rect(center=(WIDTH//2, HEIGHT//2 + 46)))
        pygame.display.flip()
        clock.tick(10)
    return choice

if __name__ == "main":
    main()