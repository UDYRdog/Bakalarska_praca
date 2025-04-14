import pygame
import math
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Projectile:
    def __init__(self, x, y, angle, speed):
        self.speed = speed
        self.angle = math.radians(angle - 90)
        self.dx = math.cos(self.angle) * self.speed
        self.dy = -math.sin(self.angle) * self.speed
        self.rect = pygame.Rect(x - 2, y - 2, 4, 4)

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        
        return (self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or
                self.rect.y < 0 or self.rect.y > SCREEN_HEIGHT)

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 0), self.rect.center, self.rect.width // 2)
