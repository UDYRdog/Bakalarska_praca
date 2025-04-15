import pygame
from pygame.locals import *

class OptionConfig:
    def __init__(self):
        self.scale_factor = 2
        
        self.keysP1 = [
            K_w,
            K_s,
            K_a,
            K_d,
            K_u,
            K_i,
            K_o
        ]
        
        self.keysP2 = [
            K_UP,
            K_DOWN,
            K_LEFT,
            K_RIGHT,
            K_v,
            K_b,
            K_n
        ]

if __name__ == "__main__":
    pygame.init()
    config = OptionConfig()
    print("Current configuration:")
    print(f"Resolution: {config.scale_factor}x (Base: 320x240)")
    print("Player 1 Controls:", [pygame.key.name(k) for k in config.keysP1])
    print("Player 2 Controls:", [pygame.key.name(k) for k in config.keysP2])