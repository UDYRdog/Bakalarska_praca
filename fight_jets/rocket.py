import pygame
import math
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Rocket:
    def __init__(self, x, y, angle, speed):
        self.speed = speed
        self.angle = math.radians(angle - 90)
        self.dx = math.cos(self.angle) * self.speed
        self.dy = -math.sin(self.angle) * self.speed
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        self.explosion_radius = 50

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        
        off_screen = (self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or
                      self.rect.y < 0 or self.rect.y > SCREEN_HEIGHT)
        return off_screen

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 0, 0), self.rect.center, self.rect.width // 2)

    def explode(self, screen):
       
        pygame.draw.circle(screen, (255, 165, 0), self.rect.center, self.explosion_radius)
