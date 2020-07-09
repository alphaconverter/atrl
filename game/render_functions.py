import tcod as libtcod
from enum import Enum, auto

from game_states import GameStates
from menus import inventory_menu, level_up_menu, character_screen
from loader_functions.tiles import *

class RenderOrder(Enum):
    STAIRS = auto()
    CORPSE = auto()
    ITEM = auto()
    ACTOR = auto()
    ACTOR_HIT = auto()

def get_names_under_mouse(mouse, entities, fov_map):
    (x, y) = (mouse.cx, mouse.cy)

    names = [entity.name for entity in entities if entity.x == x and entity.y == y and libtcod.map_is_in_fov(fov_map, entity.x, entity.y)]
    names = ', '.join(names)

    return names.capitalize()

def render_health(panel, x, y, name, value, maximum, good_color, ok_color, bad_color):
    default_color = libtcod.white
    libtcod.console_set_default_foreground(panel, default_color)
    libtcod.console_put_char(panel, x, y, HEART, libtcod.BKGND_NONE)

    val_length = len(str(value))

    if value / float(maximum) >= 0.75:
        color = good_color
    elif value / float(maximum) >= 0.25:
        color = ok_color
    else:
        color = bad_color

    libtcod.console_set_default_foreground(panel, color)

    libtcod.console_print_ex(panel, x + 1, y, libtcod.BKGND_NONE, libtcod.LEFT, '{:4}'.format(value))
    libtcod.console_set_default_foreground(panel, default_color)
    libtcod.console_print_ex(panel, x + 5, y, libtcod.BKGND_NONE, libtcod.LEFT, '/')
    libtcod.console_set_default_foreground(panel, libtcod.Color(100,118,232))
    libtcod.console_print_ex(panel, x + 6, y, libtcod.BKGND_NONE, libtcod.LEFT, '{}'.format(maximum))
    libtcod.console_set_default_foreground(panel, default_color)

def render_all(con, panel, entities, player, game_map, fov_map, message_log, screen_width, screen_height, panel_height, panel_y, mouse, game_state, current_frame_time):
    for y in range(game_map.height):
        for x in range(game_map.width):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = game_map.tiles[x][y].block_sight

            if visible:
                if wall:
                    libtcod.console_put_char(con, x, y, WALL, libtcod.BKGND_NONE)
                else:
                    libtcod.console_put_char(con, x, y, FLOOR, libtcod.BKGND_NONE)
                game_map.tiles[x][y].explored = True
            elif game_map.tiles[x][y].explored:
                if wall:
                    libtcod.console_put_char(con, x, y, WALL + 80, libtcod.BKGND_NONE)
                else:
                    libtcod.console_put_char(con, x, y, FLOOR + 80, libtcod.BKGND_NONE)

    # Draw all entities in the list
    entities_in_render_order = sorted(entities, key=lambda x: x.render_order.value)
    for entity in entities_in_render_order:
        draw_entity(con, entity, fov_map, game_map, current_frame_time)

    libtcod.console_blit(con, 0, 0, screen_width, screen_height, 0, 0, 0)

    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    # Print the game messages, one line at a time
    y = 1
    for message in message_log.messages:
        libtcod.console_set_default_foreground(panel, message.color)
        libtcod.console_print_ex(panel, message_log.x, y, libtcod.BKGND_NONE, libtcod.LEFT, message.text)
        y += 1

    render_health(panel, 1, 2, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.Color(60,163,112), libtcod.Color(242,166,94), libtcod.Color(235,86,75))

    libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Floor: {0}'.format(-game_map.dungeon_level))

    libtcod.console_set_default_foreground(panel, libtcod.Color(126,126,143))
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse(mouse, entities, fov_map))

    libtcod.console_blit(panel, 0, 0, screen_width, panel_height, 0, 0, panel_y)

    if game_state in (GameStates.SHOW_INVENTORY, GameStates.DROP_INVENTORY):
        if game_state == GameStates.SHOW_INVENTORY:
            inventory_title = 'Press the key next to an item to use it, or Esc to cancel.\n'
        else:
            inventory_title = 'Press the key next to an item to drop it, or Esc to cancel.\n'

        inventory_menu(con, inventory_title, player, screen_height, screen_width, screen_height)

    elif game_state == GameStates.LEVEL_UP:
        level_up_menu(con, 'Level up! Choose a stat to raise:', player, 40, screen_width, screen_height)

    elif game_state == GameStates.CHARACTER_SCREEN:
        character_screen(player, 30, 10, screen_width, screen_height)

def draw_entity(con, entity, fov_map, game_map, current_frame_time):
    if libtcod.map_is_in_fov(fov_map, entity.x, entity.y) or (entity.stairs and game_map.tiles[entity.x][entity.y].explored):
        libtcod.console_put_char(con, entity.x, entity.y, entity.get_tile(current_frame_time), libtcod.BKGND_NONE)

