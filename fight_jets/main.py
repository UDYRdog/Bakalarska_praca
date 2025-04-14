import pygame
import os
import sys
import serial
import math
import random
from pygame.locals import QUIT

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from enemy import Enemy, EnemyProjectile

pygame.init()
pygame.font.init()


background_path = os.path.join('Assets', 'space.png')
player_image_path = os.path.join('Assets', 'spaceship_yellow.png')
enemy_image_path = os.path.join('Assets', 'spaceship_red.png')

try:
    background = pygame.image.load(background_path)
    player_img = pygame.image.load(player_image_path)
    player_img = pygame.transform.scale(player_img, (45, 45))
    enemy_img = pygame.image.load(enemy_image_path)
    enemy_img = pygame.transform.scale(enemy_img, (45, 45))
except pygame.error as e:
    print(f"Error loading image: {e}")
    sys.exit()

# Speeds
player_speed = 20
projectile_speed = 25
rocket_speed = 30
laser_speed = 50

# Damages
PLAYER_PROJECTILE_DAMAGE = 20
PLAYER_ROCKET_DAMAGE = 40
ENEMY_PROJECTILE_DAMAGE = 20
ROCKET_EXPLOSION_DAMAGE = 40  
ROCKET_EXPLOSION_RADIUS = 100 


LIFESTEAL_RATIO = 0.2

# Cooldowns (in seconds)
projectile_cooldown = 0.2
rocket_cooldown = 1.0
laser_cooldown = 5.0
enemy_spawn_cooldown_base = 5.0
enemy_shoot_cooldown = 2.0

last_projectile_time = 0
last_rocket_time = 0
last_laser_time = 0
last_enemy_spawn_time = 0
last_enemy_shoot_time = 0


start_time = pygame.time.get_ticks()
score = 0


font = pygame.font.SysFont("Arial", 24)
game_over_font = pygame.font.SysFont("Arial", 48)


try:
    ser = serial.Serial('COM4', 115200, timeout=0.1)
except serial.SerialException as e:
    print(f"Error connecting to micro:bit: {e}")
    sys.exit()


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


class Projectile:
    def __init__(self, x, y, angle, speed, is_enemy=False):
        self.speed = speed
        self.is_enemy = is_enemy
        angle_radians = math.radians(angle - 90)
        self.dx = math.cos(angle_radians) * self.speed
        self.dy = -math.sin(angle_radians) * self.speed
        self.rect = pygame.Rect(x - 2, y - 2, 4, 4)

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        return (self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or
                self.rect.y < 0 or self.rect.y > SCREEN_HEIGHT)

    def draw(self, screen):
        color = (255, 0, 0) if self.is_enemy else (255, 255, 0)
        pygame.draw.circle(screen, color, self.rect.center, self.rect.width // 2)


class Rocket:
    def __init__(self, x, y, angle, speed):
        self.speed = speed
        angle_radians = math.radians(angle - 90)
        self.dx = math.cos(angle_radians) * self.speed
        self.dy = -math.sin(angle_radians) * self.speed
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        self.explosion_radius = ROCKET_EXPLOSION_RADIUS

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        off_screen = (self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or
                      self.rect.y < 0 or self.rect.y > SCREEN_HEIGHT)
        return off_screen

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 0, 0), self.rect.center, self.rect.width // 2)

    def explode(self, enemies, player):
        rx, ry = self.rect.center
        enemies_killed = 0
        total_damage_dealt = 0
        for enemy in enemies[:]:
            ex, ey = enemy.rect.center
            dist = math.sqrt((ex - rx)**2 + (ey - ry)**2)
            if dist <= self.explosion_radius:
                enemy.take_damage(ROCKET_EXPLOSION_DAMAGE)
                total_damage_dealt += ROCKET_EXPLOSION_DAMAGE
                if enemy.is_dead():
                    enemies.remove(enemy)
                    enemies_killed += 1

        # Lifesteal from total damage dealt by explosion
        if total_damage_dealt > 0:
            player.heal(total_damage_dealt * LIFESTEAL_RATIO)

        explosions.append(Explosion(rx, ry, self.explosion_radius))
        return enemies_killed



class Explosion:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.lifetime = 200  # ms

    def update(self, dt):
        self.lifetime -= dt
        return self.lifetime <= 0

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 165, 0), (self.x, self.y), self.radius)


def draw_health_bar(screen, current_health, max_health, x=10, y=10, width=200, height=20):
    pygame.draw.rect(screen, (255, 0, 0), (x, y, width, height))
    ratio = current_health / max_health if max_health > 0 else 0
    pygame.draw.rect(screen, (0, 255, 0), (x, y, width * ratio, height))


def get_random_edge_position():
    edge = random.choice(['top', 'bottom', 'left', 'right'])
    if edge == 'top':
        x = random.randint(0, SCREEN_WIDTH)
        y = 0
    elif edge == 'bottom':
        x = random.randint(0, SCREEN_WIDTH)
        y = SCREEN_HEIGHT
    elif edge == 'left':
        x = 0
        y = random.randint(0, SCREEN_HEIGHT)
    else:  # right
        x = SCREEN_WIDTH
        y = random.randint(0, SCREEN_HEIGHT)
    return x, y


player = Player(player_img, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, player_speed)
projectiles = []
rockets = []

enemies = []
explosions = []

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fight_jets")
clock = pygame.time.Clock()

game_over = False

running = True
while running:
    dt = clock.tick(FPS)  

    if game_over:
        
        screen.fill((0, 0, 0))
        game_over_text = game_over_font.render("Game Over", True, (255, 255, 255))
        end_text = font.render("End of the Game", True, (255, 255, 255))
        screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50))
        screen.blit(end_text, (SCREEN_WIDTH // 2 - 65, SCREEN_HEIGHT // 2))
        
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        pygame.display.flip()
        continue

    screen.blit(background, (0, 0))

    current_time = pygame.time.get_ticks()
    elapsed_time = (current_time - start_time) // 1000

    # Increase spawn rate every 30 seconds
    difficulty_level = elapsed_time // 30
    enemy_spawn_cooldown = max(1.0, 5.0 - difficulty_level * 0.5)

    # Timer and Score display
    timer_text = font.render(f"Time: {elapsed_time}s", True, (255, 255, 255))
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(timer_text, (10, 40))
    screen.blit(score_text, (10, 70))

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

    # Spawn enemy after cooldown
    if current_time - last_enemy_spawn_time > enemy_spawn_cooldown * 1000:
        x, y = get_random_edge_position()
        enemies.append(Enemy(enemy_img, x, y))
        last_enemy_spawn_time = current_time

    # Enemy shoot after cooldown
    if enemies and (current_time - last_enemy_shoot_time > enemy_shoot_cooldown * 1000):
        for enemy in enemies:
            enemy.shoot(player, projectiles)
        last_enemy_shoot_time = current_time

   
    try:
        data = ser.readline().decode('utf-8').strip()
        if data == "CENTER":
            pass
        elif data:
           
            if data.startswith("UP"):
                if data.endswith("RIGHT"):
                    player.rotate(135)
                elif data.endswith("LEFT"):
                    player.rotate(225)
                else:
                    player.rotate(180)
            elif data.startswith("DOWN"):
                if data.endswith("RIGHT"):
                    player.rotate(45)
                elif data.endswith("LEFT"):
                    player.rotate(315)
                else:
                    player.rotate(0)
            elif data.startswith("RIGHT"):
                player.rotate(90)
            elif data.startswith("LEFT"):
                player.rotate(270)

            # Movement
            elif data == "BUTTON_E":
                player.move_up()
            elif data == "BUTTON_D":
                player.move_right()
            elif data == "BUTTON_C":
                player.move_down()
            elif data == "BUTTON_F":
                player.move_left()

            # Shoot projectiles (A)
            if data == "BUTTON_A":
                if current_time - last_projectile_time > projectile_cooldown * 1000:
                    px, py = player.get_center()
                    angle = player.get_rotation_angle()
                    projectiles.append(Projectile(px, py, angle, projectile_speed, is_enemy=False))
                    last_projectile_time = current_time

            # Shoot rockets (B)
            elif data == "BUTTON_B":
                if current_time - last_rocket_time > rocket_cooldown * 1000:
                    px, py = player.get_center()
                    angle = player.get_rotation_angle()
                    rockets.append(Rocket(px, py, angle, rocket_speed))
                    last_rocket_time = current_time

         
          

    except Exception as e:
        print(f"Error reading data: {e}")

   
    for enemy in enemies[:]:
        enemy.update(player, projectiles)
        if enemy.is_dead():
            score += 1
            enemies.remove(enemy)

    
    for p in projectiles[:]:
        if p.update():
            projectiles.remove(p)

   
    for r in rockets[:]:
        if r.update():
            rockets.remove(r)

    
    

    
    for exp in explosions[:]:
        if exp.update(dt):
            explosions.remove(exp)

    
    for enemy in enemies[:]:
        for p in projectiles[:]:
            if not p.is_enemy and p.rect.colliderect(enemy.rect):
                
                enemy.take_damage(PLAYER_PROJECTILE_DAMAGE)
                
                player.heal(PLAYER_PROJECTILE_DAMAGE * LIFESTEAL_RATIO)
                projectiles.remove(p)
                if enemy.is_dead():
                    score += 1
                    enemies.remove(enemy)
                break

   
    for enemy in enemies[:]:
        for r in rockets[:]:
            if r.rect.colliderect(enemy.rect):
                
                enemies_killed = r.explode(enemies, player) 
                score += enemies_killed
                if r in rockets:
                    rockets.remove(r)
                break

    # Check collisions: enemy projectiles vs player
    for p in projectiles[:]:
        if p.is_enemy and p.rect.colliderect(player.rect):
            player.take_damage(ENEMY_PROJECTILE_DAMAGE)
            projectiles.remove(p)

    
    if player.health <= 0:
        game_over = True

    
    player.draw(screen)

    
    for enemy in enemies:
        enemy.draw(screen)

    
    for p in projectiles:
        p.draw(screen)
    for r in rockets:
        r.draw(screen)
    

    
    for exp in explosions:
        exp.draw(screen)

    
    draw_health_bar(screen, player.health, player.max_health)

    pygame.display.flip()

ser.close()
pygame.quit()
sys.exit()
