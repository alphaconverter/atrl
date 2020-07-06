import tcod as libtcod

from game_states import GameStates
from game_messages import Message
from render_functions import RenderOrder
from loader_functions.tiles import *

def kill_player(player):
    player.char = CORPSE
    return Message('You died!', libtcod.Color(235,86,75)), GameStates.PLAYER_DEAD

def kill_monster(monster):
    death_message = Message('{0} is dead!'.format(monster.name.capitalize()), libtcod.Color(235,86,75))

    monster.char = CORPSE
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.render_order = RenderOrder.CORPSE

    return death_message

