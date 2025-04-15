import pygame, os
from pygame.locals import *
from random import randint
from game import *

import config
import health
import serial 

SCALE_FACTOR = 2  
BASE_WIDTH, BASE_HEIGHT = 320, 240  
SCALED_WIDTH, SCALED_HEIGHT = BASE_WIDTH * SCALE_FACTOR, BASE_HEIGHT * SCALE_FACTOR

DEBUG = False

class KEYCONST:
    FORW = 0
    BACK = 1
    DOWN = 4
    UP = 5
    BTNA = 6
    BTNB = 7
    BTNC = 8

class STATECONST:
    STATE_IDLE = 0
    STATE_WALK = 1
    STATE_DASH = 2
    STATE_TELP = 3
    STATE_JUMPING = 4
    STATE_JUMP = 5
    STATE_BLCK = 6
    STATE_HIT  = 7
    STATE_HYPER = 8
    STATE_FALL = 9
    STATE_DOWN = 10
    STATE_ATK = 11
    STATE_WIN = 12

class Collision:
    def __init__(self, rect1, rect2):
        self.rect1 = rect1
        self.rect2 = rect2
        if rect1 == None or rect2 == None:
            self.center = None
        else:
            assert(isinstance(rect1, GameRectangle) and isinstance(rect2, GameRectangle))
            if self.collide():
                self.center = self.rect1.getCenter()+((self.rect2.getCenter()-self.rect1.getCenter())//2)
            else:
                self.center = None
    
    def collide(self):
        return (( self.rect1.position.x < self.rect2.position.x + self.rect2.width) \
        and (self.rect1.position.x + self.rect1.width > self.rect2.position.x)) \
        and (( self.rect1.position.y < self.rect2.position.y + self.rect2.height) \
        and (self.rect1.position.y + self.rect1.height > self.rect2.position.y))

class InfoSheetLoader:
    def __init__(self, file, maxlength = 8):
        self.move_list = []
        self.health = -1
        self.strength = -1
        self.speed = -1
        self.jump = -1
        self.fireballtype = 1
        print('reading move list...')
        with open(file, encoding='utf-8') as txtfile:
            for line in txtfile:
                if line.find('Info:') > -1:
                    line = line.split('/')
                    for info in line:
                        if info.find('Health: ') != -1:
                            self.health = int(info.strip('Health: '))
                        if info.find('Fireballtype: ') != -1:
                            self.fireballtype = int(info.strip('Fireballtype: '))
                        if info.find('Hyper: ') != -1:
                            string = info.strip('Hyper: ')
                            string = string.split(',')
                            self.hyper = []
                            self.hyper.append(Vector(int(string[0]),int(string[1])))
                            self.hyper.append(Vector(int(string[2]),int(string[3])))
                            self.hyper.append(Vector(int(string[4]),int(string[5])))
                        if info.find('Speed: ') != -1:
                            self.speed = int(info.strip('Speed: '))
                        if info.find('Jump: ') != -1:
                            self.jump = int(info.strip('Jump: '))
                elif line.find('Specials') > -1:
                    self.specials = {}
                    line = line.split('/')
                    line.pop(0)
                    for info in line:
                        info=info.split(':')
                        self.specials[info[0]]=int(info[1])
                else:
                    line = line.split('/')        
                    self.move_list.append(self.interpretLine(line, maxlength))
    
    def interpretLine(self, line, maxlength):
        moveline = []
        for i in range(maxlength):
            moveline.append(None)
        for frameInfo in line:
            frameInfo.strip()
            if frameInfo[0] == '#':
                continue
            frameinfo = FrameInfo(frameInfo)
            moveline[frameinfo.index] = frameinfo
        return moveline
    
    def getcharInfo(self):
        return self

class FrameInfo:
    HIT_TYPE_NONE = 0
    HIT_TYPE_LIGHT = 1
    HIT_TYPE_HARD = 2
    HIT_TYPE_FIREBALL = 3
    HIT_TYPE_THROW = 4
    HIT_TYPE_ALWAYS = 5
    HIT_TYPE_EJECT = 6
    HIT_TYPE_HYPER = 7
    START_FALL = 8 
    
    def __init__(self, frameInfo = None):
        self.index = None
        self.bool = False
        self.move = Vector(0,0)
        self.type = FrameInfo.HIT_TYPE_NONE
        self.blockable = True
        self.damage = 0
        self.hitstun = 0
        self.blockstun = 0
        self.point = None
        self.vect = None
        
        if frameInfo == None:
            return
        
        frameInfo.lower()
        frameInfo = frameInfo.split('--')
        for info in frameInfo:
            info = info.strip()
            if info.find('fi:') != -1:
                self.index = int(info.strip('fi:'))
            elif info.find('move:') != -1:
                self.move = self.getVect(info.strip('move:'))
            elif info.find('att:') != -1:
                info = info.strip('att:')
                info = info.split(',')
                self.type = int(info[0])
                self.damage = int(info[1])
                self.hitstun = int(info[2])
                self.blockstun = int(info[3])
                if self.type == self.HIT_TYPE_THROW:
                    self.blockable = False
                self.bool = True
            elif info.find('point:') != -1:
                self.point = self.getPoint(info.strip('point:'))
            elif info.find('vect:') != -1:
                self.vect = self.getVect(info.strip('vect:'))
    
    def getVect(self, string):
        string = string.split(',')
        return Vector(int(string[0]), int(string[1]))
    
    def getPoint(self, string):
        string = string.split(',')
        return Point(int(string[0]), int(string[1]))
    
    def meld(self, frameInfo, strength, hyper):
        if frameInfo.type == self.HIT_TYPE_NONE:
            return
        elif frameInfo.type == self.START_FALL:
            self.blockable = True
            self.bool = frameInfo.bool
            self.damage = None
            self.hitstun = None
            self.blockstun = None
            self.point = None
            self.vect = None
        else:
            if not (self.type == self.HIT_TYPE_HYPER and frameInfo.type == self.HIT_TYPE_HARD) or hyper>2:
                self.type = frameInfo.type
                self.blockable = frameInfo.blockable
                self.bool = frameInfo.bool
                self.damage = frameInfo.damage
                self.hitstun = frameInfo.hitstun
                self.blockstun = frameInfo.blockstun
                self.point = frameInfo.point
                self.vect = frameInfo.vect
            else: 
                self.bool = True
        
    def __str__(self):
        if self.type != self.HIT_TYPE_NONE or self.type != self.START_FALL:
            return 'FrameInfo:{} move({},{})-attk{}'.format(self.index, self.move.x, self.move.y, self.type)
        else:
            return 'FrameInfo:{} move({},{})'.format(self.index, self.move.x, self.move.y)

class Combo_count:
    def __init__(self):
        self.count = 1
        self.print_time = 0
        self.string = ''
    
    def combo(self, state):
        if state == STATECONST.STATE_HIT or state == STATECONST.STATE_FALL \
           or state == STATECONST.STATE_HYPER:
            self.count += 1
        else:
            self.count = 1
    
    def getDmgReduce(self):
        if self.count > 2:
            return (10*(self.count-2))/100
        else: 
            return 0
    
    def show(self):
        if self.count > 1:
            self.print_time = 20
            self.string = str(self.count)+' hits'

class Fireball:
    def __init__(self, sprite_list, hitbox, sprite_width, sprite_height, hit_token, facingRight = True):
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height
        self.sprite_list = sprite_list
        self.hitbox = hitbox
        self.animation = AnimationCounter(0,0)
        self.facingRight = facingRight
        self.hit_token = hit_token
        self.position = hit_token.point
        self.vector = hit_token.vect
        self.hide = True
        self.tick = 0
    
    def getSpriteLine(self):
        return self.sprite_list[self.animation.curent_anim]
    
    def getSprite(self):
        sprite = self.getSpriteLine()[self.animation.frame]
        if sprite != None and self.facingRight == False :
            sprite = pygame.transform.flip(sprite, 1, 0)
        return sprite
    
    def getGameRectLine(self, hitbox):
        return hitbox[self.animation.curent_anim]
    
    def getGameRect(self, hitbox):
        orig = self.getGameRectLine(hitbox)[self.animation.frame]
        if orig == None:
            return None
        rectangle = GameRectangle(orig.width, orig.height, orig.position) 
        if self.facingRight:
            rectangle.position += self.getPrintPoint()
        else:
            rectangle.position = self.getPrintPoint() + Point(self.sprite_width - (rectangle.position.x + rectangle.width), rectangle.position.y)
        return rectangle
    
    def object_facing(self, orig, type):
        if (isinstance(orig, tuple)):
            orig = Vector(orig[0], orig[1]) 
        if type:
            move = Vector(orig.x, orig.y)
        else: 
            move = Point(orig.x, orig.y)
        if self.facingRight == False:
            move.x = -move.x
        return move
    
    def vector_facing(self, orig):
        return self.object_facing(orig, True)
    
    def point_facing(self, orig):
        return self.object_facing(orig, False)
    
    def set_me(self, position, hit_token, facing):
        self.hide = False
        self.facingRight = facing
        self.hit_token = hit_token
        self.position = position+self.point_facing(hit_token.point)
        self.vector = self.vector_facing(hit_token.vect)
        self.animation = AnimationCounter(0,0)
    
    def tick_me(self, int):
        if self.tick < int:
            self.tick += 1
            return
        self.animation.frame += 1
        self.newFrame = True
        if (self.animation.frame >= len(self.getSpriteLine())):
            self.animation.frame = 0
            if self.animation.curent_anim == 1: 
                self.hide = True
        if (self.getSprite() == None):
            self.animation.frame = 0
            if self.animation.curent_anim == 1:  
                self.hide = True
        self.tick = 0
    
    def action(self):
        if self.hide:
            return
        self.position += self.vector
        if self.position.x > 380 or self.position.x < -60 or self.position.y < -60:
            self.hide = True
        if self.position.y > 165 and self.animation.curent_anim == 0:
            self.hit()
    
    def attack(self, other):
        if self.hide:
            return None
        
        collision = Collision(self.getGameRect(self.hitbox), other.getGameRect(other.hitBox_list)).center
            
        if collision == None:
            collision = Collision(self.getGameRect(self.hitbox), other.fireball.getGameRect(other.fireball.hitbox)).center
            if collision == None:
                return None
            else:
                self.hit()
                other.fireball.hit()
        else:
            self.hit()
            return other.get_hit(collision, self.hit_token)
    
    def hit(self):
        self.vector = (0,0)
        self.animation.set_anim(1)
        self.tick = 0
    
    def getPrintPoint(self):
        return self.position-(self.sprite_width//2, self.sprite_height//2)
        
    def print_me(self, screen):
        if self.hide:
            return
        screen.blit(self.getSprite(), self.getPrintPoint().value())
        if DEBUG:
            hitbox = self.getGameRect(self.hitbox)
            if hitbox != None :
                hitbox.print_me(screen, (255,0,0,128))

class FireballFactory:
    def __init__(self):
        sprite_width, sprite_height = 60, 60
        fireball_path = os.path.join('res', 'fireballs.png')
        fireball_hit_path = os.path.join('res', 'fireballsHit.png')
        
        self.sprites = GameObject(fireball_path, sprite_width, sprite_height, Point(0,0)).sprite_list
        self.hit_list = RectangleSheetLoader(fireball_hit_path, sprite_width, sprite_height).getRectList()
        
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height
    
    def getSpriteListFromType(self, type):
        type = (type-1)*2
        return [self.sprites[type], self.sprites[type+1]]
    
    def getHitListFromType(self, type):
        type = (type-1)*2
        return [self.hit_list[type], self.hit_list[type+1]]
    
    def createfireball(self, type, hit_token, facingRight):
        return Fireball(self.getSpriteListFromType(type), self.getHitListFromType(type), self.sprite_width, self.sprite_height, hit_token, facingRight)

class UI:
    def __init__(self):
        self.timer = Timer()
        self.scoreP1 = 0
        self.scoreP2 = 0
        self.healthbar_back = pygame.image.load(os.path.join('res', 'BackHealth.png')).convert_alpha()
        self.healthbar_front = pygame.image.load(os.path.join('res', 'FrontHealth.png')).convert_alpha()
    
    def addscore(self, toP1, toP2):
        if toP1:
            self.scoreP1 += 1
        if toP2:
            self.scoreP2 += 1
    
    def tick_me(self, int):
        self.timer.tick_me(int)
        
    def reinit(self):
        self.timer.reinit()
        
    def print_me(self, screen, healthP1, healthP2, comboP1, comboP2):
        screen.blit(self.healthbar_back, (0,0))
        healthP1.print_me(screen)
        healthP2.print_me(screen)
        screen.blit(self.healthbar_front, (0,0))
        self.timer.print_me(screen)

class Timer:
    def __init__(self):
        timer_path = os.path.join('res', 'timer.png')
        self.time = 99
        self.maxtime = 99
        self.sprites = GameObject(timer_path, 9, 12, Point(0,0)).sprite_list[0]
        self.tick = 0
        
    def reinit(self):
        self.time = self.maxtime
    
    def tick_me(self, int):
        self.tick += 1
        if self.tick > 20*int:
            self.tick = 0
            self.update_time()
    
    def update_time(self):
        if self.maxtime > 0 and self.time > 0:
            self.time -= 1
    
    def print_me(self, screen):
        point = Point(151,6)
        if self.maxtime == -1:
            screen.blit(self.sprites[10], point.value())
            screen.blit(self.sprites[11], (point+(9,0)).value())
        else:
            time10 = self.time//10
            time1 = self.time - time10*10
            screen.blit(self.sprites[time10], point.value())
            screen.blit(self.sprites[time1],(point+(9,0)).value())

class Impact:
    def __init__(self, sprite_list, position=Point(0,0)):
        self.sprite_list = sprite_list
        self.position = position
        self.animation = AnimationCounter(0,0)
        self.animation.end_anim = False
        self.tick = 0
    
    def getSprite(self):
        return self.sprite_list[self.animation.frame]
    
    def tick_me(self, int):
        if self.tick < int:
            self.tick +=1
            return
        self.animation.frame += 1
        if (self.animation.frame >= len(self.sprite_list)):
            self.animation.end_anim = True
        self.tick = 0
    
    def print_me(self, screen):
        if self.getSprite() != None:
            screen.blit(self.getSprite(), self.position.value())

class ImpactControler:
    instance = None  

    def __new__(cls):
        if cls.instance is None:
            cls.instance = object.__new__(cls)
            impact = GameObject('./res/impact.png', 28, 32, Point(0, 0))
            cls.sprite_width = 28
            cls.sprite_height = 32
            cls.impactsprites = impact.sprite_list
            cls.impactList = []
        return cls.instance
    
    def print_pos(self, position):
        return Point(position.x - self.sprite_width//2, position.y - self.sprite_height//2)
    
    def add_impact(self, type, position=Point(0,0)):
        if type != None:
            self.impactList.append(Impact(self.impactsprites[type], self.print_pos(position)))
            
    def tick_me(self, int):
        i=0
        while i < len(self.impactList):
            self.impactList[i].tick_me(int)
            if self.impactList[i].animation.end_anim:
                self.impactList.pop(i)
            else:
                i += 1
                
    def print_me(self, screen):
        for impact in self.impactList:
            impact.print_me(screen)

class Background:
    def __init__(self, file):
        self.original_image = pygame.image.load(file).convert()
        self.original_width = self.original_image.get_width()
        self.original_height = self.original_image.get_height()
        self.base_width = 320
        self.base_height = 240
        self.scale_x = self.base_width / self.original_width
        self.scale_y = self.base_height / self.original_height
        self.scale = max(self.scale_x, self.scale_y)
        self.scaled_width = int(self.original_width * self.scale)
        self.scaled_height = int(self.original_height * self.scale)
        self.sprite = pygame.transform.scale(
            self.original_image, 
            (self.scaled_width, self.scaled_height)
        )
        self.position = Point(
            (self.base_width - self.scaled_width) // 2,
            (self.base_height - self.scaled_height) // 2
        )
    
    def print_me(self, surface):
        surface.blit(self.sprite, self.position.value())

class Player(GameObject):
    def __init__(self, file, sprite_width, sprite_height, position=Point(0,0), Player2=False, alt_color=False):
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height
        char_dir = os.path.join('res', 'Char', file)
        if alt_color:
            spritefile = os.path.join(char_dir, file + 'Alt.png')
        else:
            spritefile = os.path.join(char_dir, file + '.png')
        
        GameObject.__init__(self, spritefile, sprite_width, sprite_height, position)
        hitbox_file = os.path.join(char_dir, file + 'HB.png')
        self.hitBox_list = RectangleSheetLoader(hitbox_file, sprite_width, sprite_height).getRectList()
        hit_file = os.path.join(char_dir, file + 'Hit.png')
        self.hit_list = RectangleSheetLoader(hit_file, sprite_width, sprite_height).getRectList()
        move_file = os.path.join(char_dir, file + 'Move.txt')
        self.charInfo = InfoSheetLoader(move_file).getcharInfo()
        
        self.health = health.HealthBar(self.charInfo.health, not Player2)
        self.energy = health.EnergyBar(not Player2)
        self.stick_inputs = [None]
        self.btn_inputs = [None]
        self.movestart = False
        self.combo_count = Combo_count()
        self.hyper = 0
        self.hit_token = FrameInfo()
        self.inputTick = 0 
        self.frameCount = 0
        self.moveVect = Vector(0, 0)
        self.facingRight = True
        self.throw_token = False
        self.fireball = FireballFactory().createfireball(self.charInfo.fireballtype, FrameInfo('fi:0--att:3,0,0,0--vect:0,0--point:0,0'), self.facingRight)
        self.last_inputs = []
    
    def reinit(self, point, enemy_position):
        self.health.reinit()
        self.stick_inputs = [None]
        self.btn_inputs = [None]
        self.fireball.hide = True
        self.position = point
        self.idle(enemy_position)
    
    def getGameRectLine(self, hitbox):
        return hitbox[self.animation.curent_anim]
    
    def getGameRect(self, hitbox):
        orig = self.getGameRectLine(hitbox)[self.animation.frame]
        if orig == None:
            return None
        rectangle = GameRectangle(orig.width, orig.height, orig.position) 
        if self.facingRight:
            rectangle.position += self.getPrintPoint()
        else:
            rectangle.position = self.getPrintPoint() + Point(self.sprite_width - (rectangle.position.x + rectangle.width), rectangle.position.y)
        return rectangle
    
    def set_anim(self, anim):
        self.newFrame = True
        self.animation.set_anim(anim)
        self.tick = 0
    
    def winpose(self):
        if self.getState() == STATECONST.STATE_WIN:
            if self.animation.frame == len(self.sprite_list[17])-1:
                return True
        return False
    
    def getFrameInfo(self, alter=None):
        if self.getState()==STATECONST.STATE_ATK:
            orig = self.charInfo.move_list[self.animation.curent_anim-18][self.animation.frame]
            if orig == None:
                return Vector(0,0)
            elif self.newFrame:
                if orig.type == FrameInfo.HIT_TYPE_FIREBALL:
                    if self.fireball.hide:
                        self.fireball.set_me(self.position, orig, self.facingRight)
                elif orig.type != FrameInfo.HIT_TYPE_NONE and orig.type != FrameInfo.START_FALL: 
                    self.hit_token.meld(orig, self.charInfo.strength, self.hyper)
                elif orig.type == FrameInfo.START_FALL:
                    self.moveVect = Vector(0,0)
            move = orig.move
        elif self.getState()==STATECONST.STATE_BLCK:
            move = Vector(-0.2, 0)
        elif self.getState()==STATECONST.STATE_HIT:
            move = Vector(-0.2, 0)
        elif self.getState()==STATECONST.STATE_DASH:
            move = Vector(self.charInfo.speed+5, 0)
            if self.animation.frame > 1:
                move -= (5,0)
            if self.animation.curent_anim == 3:
                move = (-move.x, move.y)
        elif self.getState()==STATECONST.STATE_TELP:
            move = Vector(2, 0) 
        else:
            return Vector(0,0)
        return self.vector_facing(move)
    
    def vector_facing(self, orig):
        if (isinstance(orig, tuple)):
            orig = Vector(orig[0], orig[1]) 
        move = Vector(orig.x, orig.y)
        if self.facingRight == False:
            move.x = -move.x
        return move
    
    def getPrintPoint(self):
        return self.position-(self.sprite_width//2, self.sprite_height)
    
    def getSprite(self):
        sprite = GameObject.getSprite(self)
        if sprite != None and self.facingRight == False :
            sprite = pygame.transform.flip(sprite, 1, 0)
        return sprite
    
    def getState(self):
        switch = self.animation.curent_anim
        if switch == 0:
            return STATECONST.STATE_IDLE
        elif switch == 1:
            return STATECONST.STATE_WALK
        elif 2 <= switch <= 3:
            return STATECONST.STATE_DASH
        elif switch == 4:
            return STATECONST.STATE_TELP
        elif switch == 5:
            return STATECONST.STATE_JUMPING
        elif 6 <= switch <= 7:
            return STATECONST.STATE_JUMP
        elif switch == 8:
            return STATECONST.STATE_BLCK
        elif 9 <= switch <= 10:
            return STATECONST.STATE_HIT
        elif switch == 11:
            return STATECONST.STATE_HYPER
        elif 12 <= switch <= 13:
            return STATECONST.STATE_FALL
        elif 14 <= switch <= 16:
            return STATECONST.STATE_DOWN
        elif switch == 17:
            return STATECONST.STATE_WIN 
        else:
            return STATECONST.STATE_ATK
    
    def tick_me(self, int):
        GameObject.tick_me(self, int)
        self.fireball.tick_me(int)
        self.health.tick_me(int)
    
    def print_me(self, screen):
        if self.getSprite() != None :
            screen.blit(self.getSprite(), self.getPrintPoint().value())
        if DEBUG:  
            hitbox = self.getGameRect(self.hitBox_list)
            if hitbox != None :
                hitbox.print_me(screen)
            hitbox = self.getGameRect(self.hit_list)
            if hitbox != None :
                hitbox.print_me(screen, (255,0,0,128))
        if self.fireball is not None:
            self.fireball.print_me(screen)
        self.energy.print_me(screen)
    
    def setInputs(self, stick_inputs, btn_inputs):
        self.btn_inputs = btn_inputs
        if len(stick_inputs) == 0:
            input_buffer = None
        else:
            input_buffer = stick_inputs
            if self.facingRight == False:
                for i in range(len(input_buffer)):
                    if input_buffer[i] == KEYCONST.BACK:
                        input_buffer[i] = KEYCONST.FORW
                    elif input_buffer[i] == KEYCONST.FORW:
                        input_buffer[i] = KEYCONST.BACK
        if input_buffer != self.stick_inputs[len(self.stick_inputs)-1]:
            self.stick_inputs.append(input_buffer)
            if len(self.stick_inputs) > 12:
                self.stick_inputs.pop(0)
            self.inputTick = 0
        else:
            self.inputTick += 1
            if self.inputTick > 8:
                self.stick_inputs = [input_buffer]
                self.inputTick = 0
    
    def input_contains_360(self):
        if len(self.stick_inputs) < 4:
            return False
        if self.input_contains(KEYCONST.DOWN):
            return self.input_list_contains([KEYCONST.BACK, KEYCONST.UP, KEYCONST.FORW, KEYCONST.DOWN]) \
                or self.input_list_contains([KEYCONST.FORW, KEYCONST.UP, KEYCONST.BACK, KEYCONST.DOWN])
        elif self.input_contains(KEYCONST.FORW):
            return self.input_list_contains([KEYCONST.UP, KEYCONST.BACK, KEYCONST.DOWN, KEYCONST.FORW]) \
                or self.input_list_contains([KEYCONST.DOWN, KEYCONST.BACK, KEYCONST.UP, KEYCONST.FORW])
        elif self.input_contains(KEYCONST.BACK):
            return self.input_list_contains([KEYCONST.UP, KEYCONST.FORW, KEYCONST.DOWN, KEYCONST.BACK]) \
                or self.input_list_contains([KEYCONST.DOWN, KEYCONST.FORW, KEYCONST.UP, KEYCONST.BACK])
        elif self.input_contains(KEYCONST.UP):
            return self.input_list_contains([KEYCONST.BACK, KEYCONST.DOWN, KEYCONST.FORW, KEYCONST.UP]) \
                or self.input_list_contains([KEYCONST.FORW, KEYCONST.DOWN, KEYCONST.BACK, KEYCONST.UP])
    
    def input_contains_charge(self, search1, search2):
        if self.input_contains(search1, 0):
            return (self.input_contains(search2, 1) or self.input_contains(search2, 2))
    
    def input_list_contains(self, list, inputIndex = -1, index = -1):
        if (len(list) < inputIndex) or (abs(inputIndex) > len(list)):
            return True
        if self.input_contains(None, index) and list[inputIndex] != None:
            return self.input_list_contains(list,inputIndex,index-1)
        if (inputIndex < -1):
            if (self.input_contains(list[inputIndex+1], index)):
                return self.input_list_contains(list,inputIndex,index-1)
        if (self.input_contains(list[inputIndex], index)):
            return self.input_list_contains(list,inputIndex-1,index-1)
        else: 
            return False
    
    def input_contains(self, search, index = -1):
        if (len(self.stick_inputs) <= index):
            return False
        if index < 0:
            if (abs(index) > len(self.stick_inputs)):
                return False
        if self.stick_inputs[index] == None:
            if search == None:
                return True
            return False
        for input in self.stick_inputs[index]:
            if input == search:
                return True
        return False
    
    def action_move(self):
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK:
            if self.input_list_contains([None, KEYCONST.FORW, None, KEYCONST.FORW], -1, -1):
                self.set_anim(2)
                self.inputs = [[KEYCONST.FORW]]
                self.position += self.vector_facing((self.charInfo.speed+5,0))
                return True
            if self.input_list_contains([None,KEYCONST.BACK, None, KEYCONST.BACK], -1, -1):
                self.set_anim(3)
                self.inputs = [[KEYCONST.BACK]]
                self.position -= self.vector_facing((self.charInfo.speed+5,0))
                return True
            if self.getState() == STATECONST.STATE_WALK and self.movestart:
                if self.input_contains(KEYCONST.FORW, -1):
                    self.position += self.vector_facing((self.charInfo.speed+2,0))
                elif self.input_contains(KEYCONST.BACK, -1):
                    self.position -= self.vector_facing((self.charInfo.speed,0))
            elif self.animation.frame != 0:
                self.movestart = True
            if self.getState() == STATECONST.STATE_IDLE:
                self.set_anim(1)
            return True
        else: 
            return False
    
    def action_jump(self):
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK:
            if self.input_contains(KEYCONST.UP, -1):
                self.set_anim(5)
        return False
        
    def jump_now(self):
        if self.getState() == STATECONST.STATE_JUMPING:
            self.set_anim(6)
            self.hyper = 0
            self.moveVect = self.vector_facing((0,-self.charInfo.jump))
            if self.input_contains(KEYCONST.FORW, -1):
                self.moveVect += self.vector_facing((self.charInfo.speed+1,0))
            elif self.input_contains(KEYCONST.BACK, -1):
                self.moveVect -= self.vector_facing((self.charInfo.speed+1,0))
            self.position += self.moveVect
            return True
        else:
            return False
    
    def action_lightHit(self):
        random = randint(0,2)
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK:
            self.set_anim(21+random)
            return True
        elif self.getState() == STATECONST.STATE_JUMP:
            self.set_anim(25+random)
            return True
        else: 
            return False
    
    def action_hardHit(self):
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK:
            self.set_anim(24)
            if self.hyper > 0:
                self.action_hyper()
            return True
        elif self.getState() == STATECONST.STATE_JUMP:
            self.set_anim(28)
            if self.hyper > 0:
                self.action_hyper()
            return True
        else: 
            return False
    
    def action_teleport(self):
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK:
            if self.hyper < 1:
                if self.energy.consume():
                    self.set_anim(4)
                    return True
        return False
    
    def action_special(self, move, boolean = False):
        if self.getState() == STATECONST.STATE_IDLE \
           or self.getState() == STATECONST.STATE_WALK \
           or (self.getState() == STATECONST.STATE_JUMPING and boolean):
            num = self.charInfo.specials.get(move, None)
            if num != None:
                self.set_anim(num)
                return True
        return False
    
    def action_air_special(self, move, boolean = False):
        if self.getState() == STATECONST.STATE_JUMP:
            num = self.charInfo.specials.get(move, None)
            if num != None:
                self.set_anim(num)
                return True
        return False
    
    def action_hyper(self):
        if self.hyper < 3 and self.hit_token.type != FrameInfo.HIT_TYPE_HYPER:
            if self.energy.consume():
                ImpactControler().add_impact(2, self.position+self.vector_facing((5,-20)))
                self.hit_token.type = FrameInfo.HIT_TYPE_HYPER
                self.hit_token.hitstun = 2
                self.hit_token.vect = self.vector_facing(self.charInfo.hyper[self.hyper]/((self.hit_token.hitstun*3)+3))
    
    def action(self, other_character, time):
        update_position = True
        if other_character.health.amIdead() and self.getState() == STATECONST.STATE_IDLE:
            if self.getState() != STATECONST.STATE_WIN:
                self.set_anim(17)
            return
        if time == 0 and self.health.health >= other_character.health.health \
           and self.getState() == STATECONST.STATE_IDLE:
            if self.getState() != STATECONST.STATE_WIN:
                self.set_anim(17)
            return
        if self.input_contains(None, -1):
            if self.getState() == STATECONST.STATE_WALK:
                self.set_anim(0)
                self.moveVect = Vector(0, 0)
        if self.btn_inputs.count(KEYCONST.BTNB)>0 and self.btn_inputs.count(KEYCONST.BTNA)>0:
            if other_character.animation.frame<1 and other_character.animation.curent_anim == 19:
                ImpactControler().add_impact(3, self.position+self.vector_facing((5,-10)))
                other_character.set_anim(20)
                other_character.frameCount = 2
                self.moveVect = Vector(0,0)
                self.position -= self.vector_facing((self.charInfo.speed+5,0))
                self.set_anim(3)
                self.frameCount = 0
            else:
                if self.getState() == STATECONST.STATE_IDLE \
                or self.getState() == STATECONST.STATE_WALK:
                    self.set_anim(18)
        elif self.btn_inputs.count(KEYCONST.BTNB)>0:
            if self.input_contains_360():
                self.action_special('360B', True)
            if self.input_list_contains([KEYCONST.FORW,KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('dpmfB')
            if self.input_list_contains([KEYCONST.BACK,KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('dpmbB')
            if self.input_list_contains([KEYCONST.FORW,KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('hcbB')
            if self.input_list_contains([KEYCONST.BACK,KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('hcfB')
            if self.input_contains_charge(KEYCONST.DOWN, KEYCONST.UP):
                self.action_special('chduB', True) 
            if self.input_contains_charge(KEYCONST.BACK, KEYCONST.FORW):
                self.action_special('chbfB')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_air_special('aqcfB')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_air_special('aqcbB')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('qcfB')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('qcbB')
            if self.input_contains(KEYCONST.DOWN):
                self.action_special('dB')
            if self.input_contains(KEYCONST.FORW):
                self.action_special('fB')
            if self.input_contains(KEYCONST.BACK):
                self.action_special('bB')
            self.action_hardHit()
        elif self.btn_inputs.count(KEYCONST.BTNC)>0:
            if self.animation.curent_anim == 24 and other_character.getState() != STATECONST.STATE_HYPER:
                self.action_hyper()
            else: 
                self.action_teleport()
        elif self.btn_inputs.count(KEYCONST.BTNA)>0:
            if self.input_contains_360():
                self.action_special('360A', True)
            if self.input_list_contains([KEYCONST.FORW,KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('dpmfA')
            if self.input_list_contains([KEYCONST.BACK,KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('dpmbA')
            if self.input_list_contains([KEYCONST.FORW,KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('hcbA')
            if self.input_list_contains([KEYCONST.BACK,KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('hcfA')
            if self.input_contains_charge(KEYCONST.DOWN, KEYCONST.UP):
                self.action_special('chduA', True)   
            if self.input_contains_charge(KEYCONST.BACK, KEYCONST.FORW):
                self.action_special('chbfA')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_air_special('aqcfA')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_air_special('aqcbA')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.FORW]):
                self.action_special('qcfA')
            if self.input_list_contains([KEYCONST.DOWN,KEYCONST.BACK]):
                self.action_special('qcbA')
            if self.input_contains(KEYCONST.DOWN):
                self.action_special('dA')
            if self.input_contains(KEYCONST.FORW):
                self.action_special('fA')
            if self.input_contains(KEYCONST.BACK):
                self.action_special('bA')
            self.action_lightHit()
        elif self.input_contains(KEYCONST.UP):
            if self.action_jump():
                update_position = False
        elif self.input_contains(KEYCONST.FORW) \
             or self.input_contains(KEYCONST.BACK):
            if self.action_move():
                update_position = False
        if update_position:
            self.position += self.getFrameInfo()
            self.position += self.moveVect
        self.newFrame = False
        self.fireball.action()
    
    def turn_around_check(self, enemy_position):
        if self.facingRight \
         and enemy_position.x < self.position.x :
            self.facingRight = False
            self.invert_inputs()
        elif self.facingRight == False \
         and enemy_position.x > self.position.x :
            self.facingRight = True
            self.invert_inputs()
    
    def invert_inputs(self):
        for input in self.stick_inputs :
            if input == None :
                continue
            for i in range(len(input)):
                if input[i] == KEYCONST.BACK:
                    input[i] = KEYCONST.FORW
                elif input[i] == KEYCONST.FORW:
                    input[i] = KEYCONST.BACK
    
    def idle(self, enemy_position):
        self.turn_around_check(enemy_position)
        if self.getState() == STATECONST.STATE_IDLE or self.getState() == STATECONST.STATE_WALK:
            return
        self.set_anim(0)
        self.moveVect = Vector(0, 0)
        self.movestart = False
    
    def move(self, vect, enemy_position, enemy_state):
        self.position += vect
        self.fireball.position+=vect
        if self.getState()== STATECONST.STATE_TELP:
            if self.animation.frame == 2:
                if self.hyper > 0:
                    self.position = enemy_position + self.vector_facing((15,0))
                    self.turn_around_check(enemy_position)
                    self.moveVect = Vector(0,0)
                    if self.position.y < 195:
                        self.set_anim(25)
                    else: 
                        self.set_anim(21)
                else: 
                    self.position = enemy_position + vect + self.vector_facing((10, 0))
        if self.position.y < 195 and self.moveVect.y < 10 \
          and self.getState() != STATECONST.STATE_HYPER and not self.hyper>0:
            self.moveVect += (0, 1)
        if 9 <= self.animation.curent_anim <= 14 and self.frameCount == 0:
                self.combo_count.show()
        if self.animation.end_anim:
            if self.frameCount != 0:
                self.frameCount -= 1
                self.animation.end_anim = False
        if self.animation.end_anim:
            if self.getState() == STATECONST.STATE_WIN:
                self.tick = 0
                self.animation.frame = len(self.sprite_list[17])-1
                return
            elif self.getState() == STATECONST.STATE_IDLE or self.getState() == STATECONST.STATE_WALK:
                self.energy.add(1)
                self.animation.end_anim = False
            self.hit_token = FrameInfo() 
            if self.getState() == STATECONST.STATE_JUMPING:
                self.jump_now()
            elif self.getState() == STATECONST.STATE_HYPER:
                if self.moveVect == Vector(0,0) or self.moveVect == self.vector_facing((-0.4,0)):
                    self.set_anim(12)
                else: 
                    self.frameCount = 5
                    self.moveVect = Vector(0,0)
            elif self.getState() == STATECONST.STATE_DOWN:
                if self.animation.curent_anim == 14 and self.position.y == 195: 
                    self.moveVect=Vector(0,0)
                    self.set_anim(15)
                    self.frameCount = 5 
                elif self.animation.curent_anim == 15 and not self.health.amIdead():
                    self.set_anim(16)
                elif self.animation.curent_anim == 16:
                    self.idle(enemy_position)
            elif self.hyper > 0 and \
                (self.animation.curent_anim == 24 or self.animation.curent_anim == 28):
                if enemy_state == STATECONST.STATE_HYPER:
                    self.set_anim(4)
            elif self.position.y >= 195:
                if self.getState() == STATECONST.STATE_FALL:
                    self.position.y = 195
                    self.moveVect.y = -3
                    self.set_anim(14)
                elif self.getState() != STATECONST.STATE_DOWN:
                    self.idle(enemy_position)
            elif self.getState() == STATECONST.STATE_FALL:
                self.set_anim(13)
            else:
                self.set_anim(6)
        if (self.getState() == STATECONST.STATE_JUMP) \
            and (self.moveVect.y > 0):
            self.set_anim(7)
        if self.position.x > 288:
            self.position.x = 288
        elif self.position.x < 32:
            self.position.x = 32
        if self.position.y > 195:
            self.position.y = 195
            if self.getState() == STATECONST.STATE_FALL :              
                self.frameCount = 0
            elif self.getState() == STATECONST.STATE_DOWN : 
                self.moveVect = Vector(0,0)
                self.frameCount = 0
            elif self.getState() != STATECONST.STATE_IDLE \
               and self.getState() != STATECONST.STATE_WALK:
                self.idle(enemy_position)
    
    def attack(self, other):
        assert(isinstance(other, Player))
        if other.getState() != STATECONST.STATE_HYPER:
            self.hyper = 0
        if self.hit_token.bool and \
        (self.hit_token.type == self.hit_token.HIT_TYPE_EJECT or self.hit_token.type == self.hit_token.HIT_TYPE_ALWAYS): 
            self.hit_token.bool = False
            return other.get_thrown(self.hit_token)
        collision = Collision(self.getGameRect(self.hit_list), other.getGameRect(other.hitBox_list)).center
        if collision == None:
            return self.fireball.attack(other)
        elif self.hit_token.bool:
            self.hit_token.bool = False
            if 24 < self.animation.curent_anim < 28: 
                if self.hyper < 0:
                    self.moveVect = self.vector_facing((2,-1)) 
            if other.position.x >= 288:
                self.moveVect += self.vector_facing((-0.4,0))
            elif other.position.x <= 32:
                self.moveVect += self.vector_facing((-0.4,0))
            hit, colision = other.get_hit(collision, self.hit_token)
            if hit == 1:
                self.energy.add(2)
            elif hit == 0:
                self.energy.add(3)
            if self.hit_token.type == FrameInfo.HIT_TYPE_THROW:
                self.set_anim(self.animation.curent_anim + 1)
            elif self.hit_token.type == FrameInfo.HIT_TYPE_HYPER:
                self.hyper += 1
            return hit, colision
        else:
            return self.fireball.attack(other)
    
    def get_hit(self, colision, hit_token):
        hit_type=0
        if hit_token.type == FrameInfo.HIT_TYPE_LIGHT \
        or hit_token.type == FrameInfo.HIT_TYPE_HARD \
        or hit_token.type == FrameInfo.HIT_TYPE_FIREBALL \
        or hit_token.type == FrameInfo.HIT_TYPE_HYPER \
        or hit_token.type == FrameInfo.HIT_TYPE_EJECT:
            hit_type=1
        elif hit_token.type == FrameInfo.HIT_TYPE_NONE \
          or hit_token.type == FrameInfo.HIT_TYPE_THROW \
          or hit_token.type == FrameInfo.HIT_TYPE_ALWAYS:
            hit_type = None
        else:
            hit_type=2
        if hit_token.type == FrameInfo.HIT_TYPE_HYPER:
            self.get_hit_hyper(hit_token.vect)
            self.frameCount = hit_token.hitstun
            self.combo_count.combo(self.getState())
            self.health.loseHp(hit_token.damage, self.combo_count.getDmgReduce())
            return hit_type, colision
        elif self.getState() == STATECONST.STATE_HYPER and hit_token.type != FrameInfo.HIT_TYPE_HARD: 
            if self.moveVect != self.vector_facing((-0.4,0)): 
                self.frameCount = 15
            self.moveVect = self.vector_facing((-0.4,0))
            self.combo_count.combo(self.getState())
            self.health.loseHp(hit_token.damage, self.combo_count.getDmgReduce())
            return hit_type, colision
        if hit_token.blockable:
            if ((self.getState() == STATECONST.STATE_IDLE or self.getState() == STATECONST.STATE_WALK) \
                and self.input_contains(KEYCONST.BACK, -1)) \
                or self.getState() == STATECONST.STATE_BLCK:
                self.set_anim(8)
                self.frameCount = hit_token.blockstun
                self.energy.add(3)
                return 0, colision
        if self.position.y < 195 or hit_token.type == FrameInfo.HIT_TYPE_HARD:
            self.combo_count.combo(self.getState())
            self.health.loseHp(hit_token.damage, self.combo_count.getDmgReduce())
            if not self.getState() == STATECONST.STATE_FALL:
                self.frameCount  = 15
            if hit_token.vect != None:
                self.get_hit_strong(hit_token.vect)
            else: 
                self.get_hit_strong() 
            return hit_type, colision
        self.combo_count.combo(self.getState())
        self.health.loseHp(hit_token.damage, self.combo_count.getDmgReduce())
        if self.health.amIdead():
            self.get_hit_strong()
        else: 
            self.get_hit_light()
        self.frameCount = hit_token.hitstun
        return hit_type, colision
    
    def get_hit_strong(self, vect = Vector(-2,-5)):
        self.set_anim(12)
        self.moveVect = self.vector_facing(vect)
    
    def get_hit_light(self, anim = -1):
        if anim == -1:
            anim = randint(0,1)
        self.set_anim(9+anim)
    
    def get_thrown(self, hit_token):
        if hit_token.type == hit_token.HIT_TYPE_ALWAYS:
            self.moveVect = self.vector_facing(hit_token.vect)
            return 1, Point(400,400)
        if hit_token.type == hit_token.HIT_TYPE_EJECT:
            self.health.loseHp(hit_token.damage, self.combo_count.getDmgReduce())
            self.get_hit_strong(hit_token.vect)
            return 1, Point(400,400)
    
    def get_hit_hyper(self, vect):
        self.set_anim(11)
        self.moveVect = vect
    
    

class Game:
    def __init__(self, screen, background, character1, character2):
        self.screen = screen
        self.base_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.config = config.OptionConfig()
        self.clock = pygame.time.Clock()
        self.input_reader = InputReader(self.config.keysP1, self.config.keysP2)
        self.background = background
        self.character1 = character1
        self.character2 = character2
        self.ui = UI()
        self.initRound()
    
    def initRound(self, toP1 = False, toP2 = False):
        self.character1.reinit(Point(40,195), Point(280,195))
        self.character2.reinit(Point(280,195), Point(40,195))
        self.background.position = Point(-160, 0)
        self.character2.facingRight = False
        self.ui.reinit()
        self.ui.addscore(toP1, toP2)
        self.color = (0,0,0,255)
        return False
        
    def center(self):
        return (self.character1.position+self.character2.position)/2
    
    def winpose(self):
        return self.character1.winpose() or self.character2.winpose() \
            or (self.character1.health.amIdead() and self.character2.health.amIdead())
        
    def push_caracters(self, colision_point):
        if self.character1.getState() == STATECONST.STATE_HYPER:
            if self.character1.position.x > 280:
                self.character1.position.x -= 3
                return
            elif self.character1.position.x < 60:
                self.character1.position.x += 3
                return
        elif self.character2.getState() == STATECONST.STATE_HYPER:
            if self.character2.position.x > 280:
                self.character2.position.x -= 3
                return
            elif self.character2.position.x < 60:
                self.character2.position.x += 3
                return
        if (self.character1.position.y < 195) or (self.character2.position.y < 195):
            if self.character1.position.x <= colision_point.x :
                self.character1.position.x -= 3
                self.character2.position.x += 3
            elif self.character1.position.x > colision_point.x :
                self.character2.position.x -= 3
                self.character1.position.x += 3
        else:
            if self.character1.position.x <= self.character2.position.x :
                self.character1.position.x -= 3
                self.character2.position.x += 3
            elif self.character1.position.x > self.character2.position.x :
                self.character2.position.x -= 3
                self.character1.position.x += 3
    
    def pause_loop(self):
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    return 'QUIT'
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        return 'RESUME'
                    if event.key == K_F5:
                        return 'QUIT'
    
    def mainloop(self):
        base_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        round_marker = (False, False)
        end_round = False
        print("start")
        
        while True:
            stick_inputs_p1, btn_inputs_P1, stick_inputs_p2, btn_inputs_P2, special = self.input_reader.getInputs()
            if special == 'PAUSE':
                special = self.pause_loop()
            if special == 'QUIT':
                return 0
            if not end_round and self.color[3] == 0:
                if self.ui.timer.time == 0 or self.character1.health.amIdead() or self.character2.health.amIdead():
                    if self.character1.health.hp > self.character2.health.hp:
                        round_marker = (True, False)
                    elif self.character1.health.hp < self.character2.health.hp:
                        round_marker = (False, True)
                    else: 
                        round_marker = (True, True)
                    end_round = True
                    self.character1.stick_inputs = [None]
                    self.character1.btn_inputs = [None]
                    self.character2.stick_inputs = [None]
                    self.character2.btn_inputs = [None]
                else:
                    self.character1.setInputs(stick_inputs_p1, btn_inputs_P1)
                    self.character2.setInputs(stick_inputs_p2, btn_inputs_P2)
            self.character1.action(self.character2, self.ui.timer.time)
            self.character2.action(self.character1, self.ui.timer.time)
            collision = Collision(self.character1.getGameRect(self.character1.hitBox_list),
                     (self.character2.getGameRect(self.character2.hitBox_list)))
            if collision.center != None:
                self.push_caracters(collision.center)
            position1, position2 = self.character1.position, self.character2.position
            self.character1.move(Vector(0,0), position2, self.character2.getState()) 
            self.character2.move(Vector(0,0), position1, self.character1.getState()) 
            impact = self.character1.attack(self.character2)
            impact2 = self.character2.attack(self.character1)
            if impact != None:
                ImpactControler().add_impact(impact[0], impact[1])
                self.character2.turn_around_check(self.character1.position)
            if impact2 != None:
                ImpactControler().add_impact(impact2[0], impact2[1])
                self.character1.turn_around_check(self.character2.position)
            base_surface.fill((0,0,0))
            self.background.print_me(base_surface)
            self.ui.print_me(base_surface,
                            self.character1.health, self.character2.health,
                            self.character1.combo_count, self.character2.combo_count)
            if self.character2.getState() == STATECONST.STATE_ATK and \
            self.character1.getState() != STATECONST.STATE_ATK:
                self.character1.print_me(base_surface)
                self.character2.print_me(base_surface)
            elif self.character1.getState() == STATECONST.STATE_DOWN and \
                self.character2.getState() == STATECONST.STATE_DOWN:
                self.character1.print_me(base_surface)
                self.character2.print_me(base_surface)
            else:
                self.character2.print_me(base_surface)
                self.character1.print_me(base_surface)
            ImpactControler().print_me(base_surface)
            if self.color[3] != 0:
                fade = pygame.Surface((BASE_WIDTH, BASE_HEIGHT)).convert_alpha()
                fade.fill(self.color)
                base_surface.blit(fade, (0,0))
            scaled_surface = pygame.transform.scale(base_surface, 
                                                (BASE_WIDTH * SCALE_FACTOR, 
                                                BASE_HEIGHT * SCALE_FACTOR))
            self.screen.blit(scaled_surface, (0, 0))
            if end_round and self.winpose():
                if self.color[3] < 255:
                    self.color = (0,0,0,self.color[3]+15)
                    if self.color[3] > 255:
                        print('ting !!')
                        self.color = (0,0,0,255)
                else:
                    end_round = False
                    self.initRound(round_marker[0], round_marker[1])
            else:
                if self.color[3] > 0:
                    self.color = (0,0,0,self.color[3]-15)
                    if self.color[3] < 0:
                        self.color = (0,0,0,0)
            tick_time = 2
            self.character1.tick_me(tick_time)
            self.character2.tick_me(tick_time)
            ImpactControler().tick_me(tick_time)
            self.ui.tick_me(tick_time)
            if self.character1.health.amIdead() or self.character2.health.amIdead():
                if self.character1.getState() == STATECONST.STATE_WIN \
                or self.character2.getState() == STATECONST.STATE_WIN:
                    self.clock.tick(30)
                else: 
                    self.clock.tick(15)     
            else: 
                self.clock.tick(30)
            pygame.display.update()

class InputReader:
    def __init__(self, keysP1, keysP2):
        self.keysP1 = keysP1
        self.keysP2 = keysP2   
        try:
            self.serial_port = serial.Serial('COM4', 115200, timeout=0.1)
        except Exception as e:
            print(f"Could not connect to Micro:bit: {e}")
            self.serial_port = None
    
    def getInputs(self):
        btn_inputs_p1 = []
        stick_inputs_p1 = []
        btn_inputs_p2 = []
        stick_inputs_p2 = []
        special = 0
        if self.serial_port and self.serial_port.in_waiting > 0:
            line = self.serial_port.readline().decode('utf-8').strip()
            if line == "BTNC":
                btn_inputs_p1.append(KEYCONST.BTNC)  
            elif line == "COMBO_1":
                stick_inputs_p1.append(KEYCONST.DOWN)
                btn_inputs_p1.append(KEYCONST.BTNA)
            elif line == "COMBO_2":
                stick_inputs_p1.append(KEYCONST.DOWN)
                btn_inputs_p1.append(KEYCONST.BTNB)
            elif line == "COMBO_3":
                stick_inputs_p1.append(KEYCONST.FORW)
                btn_inputs_p1.append(KEYCONST.BTNA)
            elif line == "COMBO_4":
                btn_inputs_p1.append(KEYCONST.BTNA)
                btn_inputs_p1.append(KEYCONST.BTNB)
            elif line == "JUMP_FORW":
                stick_inputs_p1.append(KEYCONST.UP)
                stick_inputs_p1.append(KEYCONST.FORW)
            elif line == "JUMP_BACK":
                stick_inputs_p1.append(KEYCONST.UP)
                stick_inputs_p1.append(KEYCONST.BACK)
            elif line == "BUTTON_A":
                btn_inputs_p1.append(KEYCONST.BTNB)
            elif line == "BUTTON_B":
                btn_inputs_p1.append(KEYCONST.BTNA)
            elif line == "BUTTON_C":
                stick_inputs_p1.append(KEYCONST.DOWN)
            elif line == "BUTTON_D":
                stick_inputs_p1.append(KEYCONST.FORW)
            elif line == "BUTTON_E":
                stick_inputs_p1.append(KEYCONST.UP)
            elif line == "BUTTON_F":
                stick_inputs_p1.append(KEYCONST.BACK)
        for event in pygame.event.get():
            if event.type == QUIT:
                print('quit !')
                exit()
            if event.type == KEYDOWN:
                if event.key == K_F5:
                    special = 'QUIT'
                if event.key == K_ESCAPE:
                    special = 'PAUSE'
                if event.key == self.keysP2[4]:
                    btn_inputs_p2.append(KEYCONST.BTNA)
                if event.key == self.keysP2[5]:
                    btn_inputs_p2.append(KEYCONST.BTNB)
                if event.key == self.keysP2[6]:
                    btn_inputs_p2.append(KEYCONST.BTNC)
        keys = pygame.key.get_pressed()
        if keys[self.keysP2[0]]:
            stick_inputs_p2.append(KEYCONST.UP)
        if keys[self.keysP2[1]]:
            stick_inputs_p2.append(KEYCONST.DOWN)
        if keys[self.keysP2[2]]:
            stick_inputs_p2.append(KEYCONST.BACK)
        if keys[self.keysP2[3]]:
            stick_inputs_p2.append(KEYCONST.FORW)
        return stick_inputs_p1, btn_inputs_p1, stick_inputs_p2, btn_inputs_p2, special
 
if __name__ == "__main__":
    print('loading...')
    pygame.init()
    screen = pygame.display.set_mode((SCALED_WIDTH, SCALED_HEIGHT))
    pygame.display.set_caption("Test") 
    print('loading characters...')
    player1 = Player('Rick', 120, 100)  
    player2 = Player('Ken', 120, 100, Player2=True)  
    print('loading background...')
    background = Background('../res/Background/Bckgrnd0.png')  
    print('creating game...')
    game = Game(screen, background, player1, player2)
    game.mainloop()