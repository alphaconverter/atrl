import tcod as libtcod
import warnings
import sys
import time

sys.path.append('game')

from entity import get_blocking_entities_at_location, Entity
from input_handlers import handle_keys, handle_mouse, handle_main_menu
from game_messages import Message
from game_states import GameStates
from death_functions import kill_monster, kill_player
from loader_functions.initialize_new_game import get_constants, get_game_variables
from loader_functions.data_loaders import load_game, save_game
from loader_functions.tiles import *
from menus import main_menu, message_box
from render_functions import render_all, RenderOrder
from fov_functions import initialize_fov, recompute_fov

import warnings # disable deprecation warnings
warnings.simplefilter("ignore")

def play_game(player, entities, game_map, message_log, game_state, con, panel, constants):
    fov_recompute = True
    fov_map = initialize_fov(game_map)

    key = libtcod.Key()
    mouse = libtcod.Mouse()

    game_state = GameStates.PLAYERS_TURN
    previous_game_state = game_state
    targeting_item = None

    frame_cycle_duration = constants['frame_cycle_duration']
    current_frame_time = 0

    effect_stack = []
    effect_animation_duration = constants['effect_animation_duration']
    animation_active = False
    effect_entities = []

    max_delta = constants['max_delta']
    last_tick = time.time()
    while not libtcod.console_is_window_closed():
        tick = time.time()
        delta = tick - last_tick
        last_tick = tick

        current_frame_time += delta
        if current_frame_time > frame_cycle_duration:
            current_frame_time -= frame_cycle_duration

        if fov_recompute:
            recompute_fov(fov_map, player.x, player.y, constants['fov_radius'], constants['fov_light_walls'], constants['fov_algorithm'])

        render_all(con, panel, entities + effect_entities, player, game_map, fov_map, message_log, constants['screen_width'], constants['screen_height'], constants['panel_height'], constants['panel_y'], mouse, game_state, current_frame_time)
        fov_recompute = False

        libtcod.console_flush()

        if delta < max_delta:
            time.sleep(max_delta - delta)

        #NOTE: we may not be rescheduled *exactly* after (MAX_DELTA - delta) seconds, but we do not care :p

        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        user_input = key.vk != libtcod.KEY_NONE #NOTE: mouse input [?]

        # animation system:
        if not user_input and animation_active:
            animation_timer -= delta
            if animation_timer < 0:
                effect_entities = []
                animation_active = False
            continue

        if not user_input and len(effect_stack) > 0:
            result = effect_stack.pop(0)
            if 'damaged_entity' in result:
                entity = result['damaged_entity']
                tile = entity.tiles[0]
                hit_entity = Entity(entity.x, entity.y, [tile + 32, tile], 'Annoyed ' + entity.name, frame_cycle_duration, blocks=False, render_order=RenderOrder.ACTOR_HIT)
                effect_entities.append(hit_entity)
            else: # fire_entity
                coords = result['explosion_coords']
                for x, y in coords:
                    fire_entity = Entity(x, y, [FIRE, SPARK], 'Fire', frame_cycle_duration, blocks=False, render_order=RenderOrder.ITEM)
                    effect_entities.append(fire_entity)

            for e in effect_entities:
                e.is_effect = True
                e.anim_offset = current_frame_time + (effect_animation_duration / 2)
                if e.anim_offset > frame_cycle_duration:
                    e.anim_offset -= frame_cycle_duration

            animation_timer = effect_animation_duration
            animation_active = True
            continue

        if animation_active:
            effect_stack = []
            effect_entities = []
            animation_active = False

        action = handle_keys(key, game_state)
        mouse_action = handle_mouse(mouse)

        move = action.get('move')
        exit = action.get('exit')
        pickup = action.get('pickup')
        wait = action.get('wait')
        show_inventory = action.get('show_inventory')
        drop_inventory = action.get('drop_inventory')
        inventory_index = action.get('inventory_index')
        take_stairs = action.get('take_stairs')
        level_up = action.get('level_up')
        show_character_screen = action.get('show_character_screen')
        fullscreen = action.get('fullscreen')

        left_click = mouse_action.get('left_click')
        right_click = mouse_action.get('right_click')

        player_turn_results = []

        if move and game_state == GameStates.PLAYERS_TURN:
            dx, dy = move
            destination_x = player.x + dx
            destination_y = player.y + dy
            if not game_map.is_blocked(destination_x, destination_y):
                target = get_blocking_entities_at_location(entities, destination_x, destination_y)
                if target:
                    attack_results = player.fighter.attack(target)
                    player_turn_results.extend(attack_results)
                else:
                    player.move(dx, dy)
                    fov_recompute = True

                game_state = GameStates.ENEMY_TURN
        elif wait:
            game_state = GameStates.ENEMY_TURN

        elif pickup and game_state == GameStates.PLAYERS_TURN:
            for entity in entities:
                if entity.item and entity.x == player.x and entity.y == player.y:
                    pickup_results = player.inventory.add_item(entity)
                    player_turn_results.extend(pickup_results)
                    break
            else:
                message_log.add_message(Message('There is nothing here to pick up.', libtcod.Color(255, 228, 120)))

        if show_inventory:
            previous_game_state = game_state
            game_state = GameStates.SHOW_INVENTORY

        if drop_inventory:
            previous_game_state = game_state
            game_state = GameStates.DROP_INVENTORY

        if inventory_index is not None and previous_game_state != GameStates.PLAYER_DEAD and inventory_index < len(player.inventory.items):
            item = player.inventory.items[inventory_index]
            if game_state == GameStates.SHOW_INVENTORY:
                player_turn_results.extend(player.inventory.use(item, entities=entities, fov_map=fov_map))
            elif game_state == GameStates.DROP_INVENTORY:
                player_turn_results.extend(player.inventory.drop_item(item))

        if take_stairs and game_state == GameStates.PLAYERS_TURN:
            for entity in entities:
                if entity.stairs and entity.x == player.x and entity.y == player.y:
                    entities = game_map.next_floor(player, message_log, constants)
                    fov_map = initialize_fov(game_map)
                    fov_recompute = True
                    libtcod.console_clear(con)
                    break
            else:
                message_log.add_message(Message('There are no stairs here.', libtcod.Color(255, 228, 120)))

        if level_up:
            if level_up == 'hp':
                player.fighter.base_max_hp += 20
                player.fighter.hp += 20
            elif level_up == 'str':
                player.fighter.base_power += 1
            elif level_up == 'def':
                player.fighter.base_defense += 1

            game_state = previous_game_state

        if show_character_screen:
            previous_game_state = game_state
            game_state = GameStates.CHARACTER_SCREEN

        if game_state == GameStates.TARGETING:
            if left_click:
                target_x, target_y = left_click
                item_use_results = player.inventory.use(targeting_item, entities=entities, fov_map=fov_map, target_x=target_x, target_y=target_y, game_map=game_map)
                player_turn_results.extend(item_use_results)
            elif right_click:
                player_turn_results.append({'targeting_cancelled': True})

        if exit:
            if game_state in (GameStates.SHOW_INVENTORY, GameStates.DROP_INVENTORY, GameStates.CHARACTER_SCREEN):
                game_state = previous_game_state
            elif game_state == GameStates.TARGETING:
                player_turn_results.append({'targeting_cancelled': True})
            else:
                save_game(player, entities, game_map, message_log, game_state)
                return True

        if fullscreen:
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

        effect_stack.extend([result for result in player_turn_results if ('damaged_entity' in result or 'explosion_coords' in result)])
        for player_turn_result in player_turn_results:
            message = player_turn_result.get('message')
            dead_entity = player_turn_result.get('dead')
            item_added = player_turn_result.get('item_added')
            item_consumed = player_turn_result.get('consumed')
            item_dropped = player_turn_result.get('item_dropped')
            equip = player_turn_result.get('equip')
            targeting = player_turn_result.get('targeting')
            targeting_cancelled = player_turn_result.get('targeting_cancelled')
            xp = player_turn_result.get('xp')

            if message:
                message_log.add_message(message)

            if targeting_cancelled:
                game_state = previous_game_state
                message_log.add_message(Message('Targeting cancelled'))

            if xp:
                leveled_up = player.level.add_xp(xp)
                message_log.add_message(Message('You gain {0} experience points.'.format(xp)))

                if leveled_up:
                    message_log.add_message(Message('Your battle skills grow stronger! You reached level {0}'.format(player.level.current_level) + '!', libtcod.Color(255, 228, 120)))
                    previous_game_state = game_state
                    game_state = GameStates.LEVEL_UP

            if dead_entity:
                if dead_entity == player:
                    message, game_state = kill_player(dead_entity)
                else:
                    message = kill_monster(dead_entity)

                message_log.add_message(message)

            if item_added:
                entities.remove(item_added)
                game_state = GameStates.ENEMY_TURN

            if item_consumed:
                game_state = GameStates.ENEMY_TURN

            if item_dropped:
                entities.append(item_dropped)
                game_state = GameStates.ENEMY_TURN

            if equip:
                equip_results = player.equipment.toggle_equip(equip)

                for equip_result in equip_results:
                    equipped = equip_result.get('equipped')
                    dequipped = equip_result.get('dequipped')

                    if equipped:
                        message_log.add_message(Message('You equipped the {0}'.format(equipped.name)))

                    if dequipped:
                        message_log.add_message(Message('You dequipped the {0}'.format(dequipped.name)))

                game_state = GameStates.ENEMY_TURN

            if targeting:
                previous_game_state = GameStates.PLAYERS_TURN
                game_state = GameStates.TARGETING

                targeting_item = targeting

                message_log.add_message(targeting_item.item.targeting_message)

        if game_state == GameStates.ENEMY_TURN:
            for entity in entities:
                if entity.ai:
                    enemy_turn_results = entity.ai.take_turn(player, fov_map, game_map, entities)
                    effect_stack.extend([result for result in enemy_turn_results if 'damaged_entity' in result])

                    for enemy_turn_result in enemy_turn_results:
                        message = enemy_turn_result.get('message')
                        dead_entity = enemy_turn_result.get('dead')

                        if message:
                            message_log.add_message(message)

                        if dead_entity:
                            if dead_entity == player:
                                message, game_state = kill_player(dead_entity)
                            else:
                                message = kill_monster(dead_entity)

                            message_log.add_message(message)

                            if game_state == GameStates.PLAYER_DEAD:
                                break
                    if game_state == GameStates.PLAYER_DEAD:
                        break
            else:
                game_state = GameStates.PLAYERS_TURN

def main():
    constants = get_constants()

    libtcod.console_set_custom_font('res/tiles.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_CP437, 16, 28)
    libtcod.console_init_root(constants['screen_width'], constants['screen_height'], constants['window_title'], True)

    con = libtcod.console_new(constants['screen_width'], constants['screen_height'])
    panel = libtcod.console_new(constants['screen_width'], constants['panel_height'])

    # load tiles
    idx = 256
    for y in range(16, 28):
        libtcod.console_map_ascii_codes_to_font(idx, 16, 0, y)
        idx += 16

    player = None
    entities = []
    game_map = None
    message_log = None
    game_state = None

    show_main_menu = True
    show_load_error_message = False

    main_menu_bg_image = libtcod.image_load('menu_bg.png')

    key = libtcod.Key()
    mouse = libtcod.Mouse()

    MAX_DELTA = 0.01
    last_tick = time.time()
    while not libtcod.console_is_window_closed():
        tick = time.time()
        delta = tick - last_tick
        last_tick = tick

        if delta < MAX_DELTA:
            time.sleep(MAX_DELTA - delta)

        if show_main_menu:
            main_menu(con, main_menu_bg_image, constants['screen_width'], constants['screen_height'])

            if show_load_error_message:
                message_box(con, 'No save game to load', 32, constants['screen_width'], constants['screen_height'])

            libtcod.console_flush()

            libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)

            action = handle_main_menu(key)

            new_game = action.get('new_game')
            load_saved_game = action.get('load_game')
            exit_game = action.get('exit')

            if show_load_error_message and (new_game or load_saved_game or exit_game):
                show_load_error_message = False
            elif new_game:
                player, entities, game_map, message_log, game_state = get_game_variables(constants)
                game_state = GameStates.PLAYERS_TURN
                show_main_menu = False
            elif load_saved_game:
                try:
                    player, entities, game_map, message_log, game_state = load_game()
                    show_main_menu = False
                except FileNotFoundError:
                    show_load_error_message = True
            elif exit_game:
                break

        else:
            libtcod.console_clear(con)
            play_game(player, entities, game_map, message_log, game_state, con, panel, constants)
            show_main_menu = True

if __name__ == '__main__':
    main()

