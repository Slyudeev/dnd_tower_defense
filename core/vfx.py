# core/vfx.py
import pygame
import random

class Particle:
    def __init__(self, x, y, color, speed, duration):
        self.x = x
        self.y = y
        self.color = color
        # Случайное направление разлета
        self.vx = random.uniform(-speed, speed)
        self.vy = random.uniform(-speed, speed)
        self.lifetime = duration
        self.max_lifetime = duration
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        self.size = max(0, self.size - dt * 2)

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, alpha), (self.size, self.size), self.size)
            surface.blit(surf, (self.x - self.size, self.y - self.size))

class FloatingText:
    def __init__(self, x, y, text, color, is_crit=False):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.vy = -30 # Летит вверх
        self.lifetime = 1.0 if not is_crit else 1.5
        self.max_lifetime = self.lifetime
        
        font_size = 30 if is_crit else 20
        self.font = pygame.font.SysFont(None, font_size, bold=is_crit)

    def update(self, dt):
        self.y += self.vy * dt
        self.lifetime -= dt

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            txt_surf = self.font.render(self.text, True, self.color)
            txt_surf.set_alpha(alpha)
            
            # Добавляем черную обводку для читаемости
            outline = self.font.render(self.text, True, (0, 0, 0))
            outline.set_alpha(alpha)
            surface.blit(outline, (self.x - outline.get_width()//2 + 1, self.y + 1))
            
            surface.blit(txt_surf, (self.x - txt_surf.get_width()//2, self.y))

class VFXManager:
    def __init__(self):
        self.particles = []
        self.texts = []

    def add_hit_effect(self, x, y, color=(200, 50, 50)):
        # Создаем взрыв из 10 частиц
        for _ in range(10):
            self.particles.append(Particle(x, y, color, speed=100, duration=0.5))

    def add_floating_text(self, x, y, amount, is_crit=False):
        text = f"{amount}!" if is_crit else str(amount)
        color = (255, 215, 0) if is_crit else (255, 255, 255)
        self.texts.append(FloatingText(x, y, text, color, is_crit))

    def update(self, dt):
        for p in self.particles: p.update(dt)
        for t in self.texts: t.update(dt)
        self.particles = [p for p in self.particles if p.lifetime > 0]
        self.texts = [t for t in self.texts if t.lifetime > 0]

    def draw(self, surface):
        for p in self.particles: p.draw(surface)
        for t in self.texts: t.draw(surface)

# Глобальный менеджер эффектов
vfx = VFXManager()