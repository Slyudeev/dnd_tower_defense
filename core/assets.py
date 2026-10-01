# core/assets.py
import pygame
import os

_image_cache = {}

def get_image(filename, size, fallback_color=(255, 0, 255), is_circle=False):
    """
    Пытается загрузить картинку. Если файла нет - создает временную заглушку.
    """
    if filename in _image_cache:
        return _image_cache[filename]
        
    path = os.path.join("assets", filename)
    
    if os.path.exists(path):
        # Если картинка есть в папке assets/
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, size)
        img.set_colorkey((255, 255, 255))
    else:
        # Если картинки нет - создаем прозрачную поверхность (заглушку)
        img = pygame.Surface(size, pygame.SRCALPHA)
        if is_circle:
            # Для врагов и пуль рисуем круг
            pygame.draw.circle(img, fallback_color, (size[0]//2, size[1]//2), size[0]//2)
        else:
            # Для башен рисуем квадрат с рамкой
            img.fill(fallback_color)
            pygame.draw.rect(img, (255, 255, 255), img.get_rect(), 2) # Белая рамка
            
    _image_cache[filename] = img
    return img