import pygame
import os
import config
from game import Point
import game_round

if __name__ == "__main__":
    print('loading...')
    
    pygame.init()
    
    SCALE_FACTOR = 2
    BASE_WIDTH, BASE_HEIGHT = 320, 240
    screen = pygame.display.set_mode((BASE_WIDTH * SCALE_FACTOR, BASE_HEIGHT * SCALE_FACTOR))
    pygame.display.set_caption("Fighter game")
    
    print('loading characters...')
    player1 = game_round.Player('Ken', 120, 100)
    player2 = game_round.Player('Rick', 120, 100, Player2=True)
    
    print('loading background...')
    background_path = os.path.join('res', 'Background', 'Figback.jpg')
    background = game_round.Background(background_path)
    
    print('creating game...')
    game = game_round.Game(screen, background, player1, player2)
    game.mainloop()