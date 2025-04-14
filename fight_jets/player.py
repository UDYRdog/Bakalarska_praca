import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Player:
    def __init__(self, image, x, y, speed):
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed
        self.rotation_angle = 0
        self.max_health = 100
        self.health = self.max_health  

    def rotate(self, angle):
        self.rotation_angle = angle

    def move_up(self):
        if self.rect.top > 0:
            self.rect.y -= self.speed

    def move_down(self):
        if self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += self.speed

    def move_left(self):
        if self.rect.left > 0:
            self.rect.x -= self.speed

    def move_right(self):
        if self.rect.right < SCREEN_WIDTH:
            self.rect.x += self.speed

    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.image, self.rotation_angle)
        new_rect = rotated_image.get_rect(center=self.rect.center)
        screen.blit(rotated_image, new_rect)

    def get_center(self):
        return self.rect.center

    def get_rotation_angle(self):
        return self.rotation_angle

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def heal(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
