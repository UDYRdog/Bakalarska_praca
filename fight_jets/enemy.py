import pygame
import math
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_HEALTH, ENEMY_SHOOT_INTERVAL, ENEMY_PROJECTILE_SPEED

class Enemy:
    def __init__(self, image, x, y):
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.health = ENEMY_HEALTH
        self.last_shoot_time = 0
        self.rotation_angle = 0

    def update(self, player, projectiles):
        px, py = player.get_center()
        ex, ey = self.rect.center
        
       
        angle_radians = math.atan2(py - ey, px - ex)
        
        
        angle_degrees = math.degrees(angle_radians)
        
        
        angle_degrees = -angle_degrees
        
        
        self.rotation_angle = angle_degrees + 90

        
        speed = 2
        self.rect.x += math.cos(angle_radians) * speed
        self.rect.y += math.sin(angle_radians) * speed

        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shoot_time > ENEMY_SHOOT_INTERVAL:
            self.shoot(player, projectiles)
            self.last_shoot_time = current_time

    def shoot(self, player, projectiles):
        px, py = player.get_center()
        ex, ey = self.rect.center
        
        shoot_angle = math.degrees(math.atan2(py - ey, px - ex))
        projectiles.append(EnemyProjectile(ex, ey, shoot_angle, ENEMY_PROJECTILE_SPEED))

    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.image, self.rotation_angle)
        new_rect = rotated_image.get_rect(center=self.rect.center)
        screen.blit(rotated_image, new_rect)

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def is_dead(self):
        return self.health <= 0


class EnemyProjectile:
    def __init__(self, x, y, angle, speed):
        self.is_enemy = True
        rad = math.radians(angle)
        self.dx = math.cos(rad) * speed
        self.dy = math.sin(rad) * speed
        self.rect = pygame.Rect(x - 5, y - 5, 10, 10)

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        return (self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or
                self.rect.y < 0 or self.rect.y > SCREEN_HEIGHT)

    def draw(self, screen):
        pygame.draw.circle(screen, (0, 255, 0), self.rect.center, self.rect.width // 2)
