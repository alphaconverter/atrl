import tcod as libtcod

from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from components.item import Item
from components.equipment import Equipment
from components.equippable import Equippable
from entity import Entity
from equipment_slots import EquipmentSlots
from game_messages import *
from loader_functions.tiles import *
from game_states import GameStates
from map_objects.game_map import GameMap
from render_functions import RenderOrder
from item_functions import cast_lightning, heal, cast_fireball, cast_confuse

def get_constants():
    window_title = 'ATRL: A Tiny RogueLike'

    screen_width = 64
    screen_height = 36

    panel_height = 7
    panel_y = screen_height - panel_height

    message_x = 20
    message_width = screen_width - message_x
    message_height = panel_height - 1

    map_width = screen_width
    map_height = screen_height - panel_height

    room_max_size = 8
    room_min_size = 5
    max_rooms = 20

    fov_algorithm = 0
    fov_light_walls = True
    fov_radius = 8

    max_monsters_per_room = 3
    max_items_per_room = 2

    max_delta = 0.01

    frame_cycle_duration = 1.5

    effect_animation_duration = 0.25
    assert(effect_animation_duration < frame_cycle_duration / 2)

    constants = {
        'window_title': window_title,
        'screen_width': screen_width,
        'screen_height': screen_height,
        'panel_height': panel_height,
        'panel_y': panel_y,
        'message_x': message_x,
        'message_width': message_width,
        'message_height': message_height,
        'map_width': map_width,
        'map_height': map_height,
        'room_max_size': room_max_size,
        'room_min_size': room_min_size,
        'max_rooms': max_rooms,
        'fov_algorithm': fov_algorithm,
        'fov_light_walls': fov_light_walls,
        'fov_radius': fov_radius,
        'max_monsters_per_room': max_monsters_per_room,
        'max_items_per_room': max_items_per_room,
        'max_delta': max_delta,
        'frame_cycle_duration': frame_cycle_duration,
        'effect_animation_duration': effect_animation_duration,
        'debug': True,
    }

    return constants

def get_game_variables(constants):
    fighter_component = Fighter(hp=100, defense=1, power=2)
    inventory_component = Inventory(20)
    level_component = Level()
    fcd = constants['frame_cycle_duration']
    equipment_component = Equipment()
    player = Entity(0, 0, [PLAYER, PLAYER + 16], 'Player', fcd, blocks=True, render_order=RenderOrder.ACTOR, fighter=fighter_component, inventory=inventory_component, level=level_component, equipment=equipment_component)
    entities = [player]

    equippable_component = Equippable(EquipmentSlots.MAIN_HAND, power_bonus=2)
    axe = Entity(0, 0, [AXE], 'Axe', fcd, equippable=equippable_component)
    player.inventory.add_item(axe)
    player.equipment.toggle_equip(axe)

    debug = constants['debug']
    if debug:
        item_component = Item(use_function=cast_fireball, targeting=True, targeting_message=Message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.Color(134,167,237)), damage=25, radius=3)
        item = Entity(0, 0, [FIRE_SCROLL], 'Fireball Scroll', fcd, render_order=RenderOrder.ITEM, item=item_component)
        player.inventory.add_item(item)
        item_component = Item(use_function=cast_lightning, damage=40, maximum_range=5)
        item = Entity(0, 0, [LIGHT_SCROLL], 'Lightning Scroll', fcd, render_order=RenderOrder.ITEM, item=item_component)
        player.inventory.add_item(item)
        item_component = Item(use_function=cast_confuse, targeting=True, targeting_message=Message( 'Left-click an enemy to confuse it, or right-click to cancel.', libtcod.Color(134,167,237)))
        item = Entity(0, 0, [CONF_SCROLL], 'Confusion Scroll', fcd, render_order=RenderOrder.ITEM, item=item_component)
        player.inventory.add_item(item)

    game_map = GameMap(constants['map_width'], constants['map_height'])
    game_map.make_map(constants['max_rooms'], constants['room_min_size'], constants['room_max_size'], constants['map_width'], constants['map_height'], player, entities, fcd)

    message_log = MessageLog(constants['message_x'], constants['message_width'], constants['message_height'])

    game_state = GameStates.PLAYERS_TURN

    return player, entities, game_map, message_log, game_state
