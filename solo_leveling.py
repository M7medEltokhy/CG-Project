# main.py
import pygame
import sys
import os
import math

# ---------- إعدادات عامة ----------
WIDTH, HEIGHT = 1000, 700
FPS = 60
BG_COLOR = (30, 30, 40)
SHOW_FPS = False

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Solo Leveling - Interactive Object")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# ---------- تحميل الصور ----------
IMAGE_PATH = "solo_leveling.jpg"
use_image = os.path.exists(IMAGE_PATH)
if use_image:
    orig_image = pygame.image.load(IMAGE_PATH).convert_alpha()
else:
    orig_image = None

# دالة لإنشاء قناع دائري ناعم (soft circular mask)
def create_circular_mask(size, softness=2):
    radius = size // 2
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - radius, y - radius)
            if dist < radius - softness:
                alpha = 255
            elif dist < radius + softness:
                alpha = int(255 * (1 - (dist - (radius - softness)) / (2 * softness)))
            else:
                alpha = 0
            mask.set_at((x, y), (255, 255, 255, alpha))
    return mask

class GameObject:
    def __init__(self, x, y, image=None, size=(160, 160)):
        self.x = x
        self.y = y
        self.angle = 0.0
        self.scale = 1.0
        self.base_size = size
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

        # Spin animation
        self.is_spinning = False
        self.spin_target = 0.0
        self.spin_speed = 720.0  # degrees per second

        # تحضير الصورة الدائرية الناعمة
        self.original_surface = pygame.Surface(size, pygame.SRCALPHA)
        if image:
            # تغيير حجم الصورة لتناسب الدائرة
            scaled = pygame.transform.smoothscale(image, size)
            self.original_surface.blit(scaled, (0, 0))
        else:
            # رسم دائرة ملونة مع نقطة بيضاء لتوضيح الاتجاه
            pygame.draw.circle(self.original_surface, (200, 120, 60), (size[0]//2, size[1]//2), size[0]//2)
            # نقطة بيضاء في الأعلى لتوضيح الاتجاه
            pygame.draw.circle(self.original_surface, (255, 255, 255),
                             (size[0]//2, size[0]//2 - size[0]//3), max(8, size[0]//10))

        # تطبيق القناع الدائري الناعم
        mask = create_circular_mask(size[0], softness=6)
        self.original_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # حفظ النسخة الأصلية للتحويل لاحقًا
        self.base_image = self.original_surface.copy()

    def get_rect(self):
        size = self.base_image.get_size()
        w = int(size[0] * self.scale)
        h = int(size[1] * self.scale)
        return pygame.Rect(self.x - w//2, self.y - h//2, w, h)

    def draw(self, surf):
        # تكبير/تصغير + دوران مع الحواف الناعمة
        rotated = pygame.transform.rotozoom(self.base_image, -self.angle, self.scale)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(rotated, rect)

    def point_inside(self, px, py):
        # فحص التصادم بدقة دائرية (وليس مستطيل)
        dx = px - self.x
        dy = py - self.y
        distance = math.hypot(dx, dy)
        radius = (self.base_image.get_width() // 2) * self.scale
        return distance <= radius

    def start_spin_360(self):
        if not self.is_spinning:
            self.is_spinning = True
            self.spin_target = self.angle + 360.0

    def update_spin(self, dt):
        if not self.is_spinning:
            return
        step = self.spin_speed * dt
        remaining = self.spin_target - self.angle
        if abs(remaining) <= step:
            self.angle = self.spin_target
            self.is_spinning = False
        else:
            self.angle += math.copysign(step, remaining)
            self.angle %= 360

# إنشاء الكائن
obj = GameObject(WIDTH // 2, HEIGHT // 2, image=orig_image, size=(200, 200))

# الخلفية
BG_IMAGE_PATH = "solo_leveling.jpg"
if os.path.exists(BG_IMAGE_PATH):
    bg_image = pygame.transform.smoothscale(pygame.image.load(BG_IMAGE_PATH).convert(), (WIDTH, HEIGHT))
else:
    bg_image = None

def draw_hud(surf, obj, fps):
    lines = [
        f"Position: ({int(obj.x)}, {int(obj.y)})",
        f"Scale: {obj.scale:.2f}x",
        f"Angle: {obj.angle:.1f}°",
        "",
        "Controls:",
        "• Drag with mouse = Move",
        "• Mouse wheel / +/- = Zoom",
        "• Q/E = Rotate 15° rotate   Space = Spin 360°",
        "• R = Reset position"
    ]
    for i, line in enumerate(lines):
        color = (255, 255, 100) if i == 4 else (230, 230, 230)
        txt = font.render(line, True, color)
        surf.blit(txt, (12, 12 + i * 26))

# ---------- الحلقة الرئيسية ----------
running = True
move_speed = 400
angular_follow_speed = 720

while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if event.button == 1:  # Left click
                if obj.point_inside(mx, my):
                    obj.dragging = True
                    obj.offset_x = obj.x - mx
                    obj.offset_y = obj.y - my
            elif event.button == 4:  # Wheel up
                obj.scale = min(6.0, obj.scale + 0.15)
            elif event.button == 5:  # Wheel down
                obj.scale = max(0.2, obj.scale - 0.15)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                obj.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if obj.dragging:
                mx, my = pygame.mouse.get_pos()
                obj.x = mx + obj.offset_x
                obj.y = my + obj.offset_y

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                obj.scale = min(6.0, obj.scale + 0.15)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                obj.scale = max(0.2, obj.scale - 0.15)
            elif event.key == pygame.K_q:
                obj.angle = (obj.angle - 15) % 360
            elif event.key == pygame.K_e:
                obj.angle = (obj.angle + 15) % 360
            elif event.key == pygame.K_r:
                obj.x, obj.y = WIDTH // 2, HEIGHT // 2
                obj.angle = 0
                obj.scale = 1.0
                obj.is_spinning = False
            elif event.key == pygame.K_SPACE:
                obj.start_spin_360()

    # حركة بالكيبورد
    keys = pygame.key.get_pressed()
    dx = dy = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
    if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
    if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1
    if dx or dy:
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length
        obj.x += dx * move_speed * dt
        obj.y += dy * move_speed * dt

    # تحديث الدوران الكامل
    obj.update_spin(dt)

    # تتبع الماوس بالدوران (عندما لا يدور 360)
    if not obj.is_spinning:
        mx, my = pygame.mouse.get_pos()
        target = math.degrees(math.atan2(my - obj.y, mx - obj.x))
        diff = (target - obj.angle + 180) % 360 - 180
        step = angular_follow_speed * dt
        if abs(diff) < step:
            obj.angle += diff
        else:
            obj.angle += math.copysign(step, diff)
        obj.angle %= 360

    # حدود الشاشة
    radius = (obj.base_image.get_width() // 2) * obj.scale
    obj.x = max(radius, min(WIDTH - radius, obj.x))
    obj.y = max(radius, min(HEIGHT - radius, obj.y))

    # الرسم
    if bg_image:
        screen.blit(bg_image, (0, 0))
    else:
        screen.fill(BG_COLOR)

    obj.draw(screen)
    draw_hud(screen, obj, clock.get_fps())

    pygame.display.flip()

pygame.quit()
sys.exit()