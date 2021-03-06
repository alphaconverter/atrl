import tcod as libtcod
import math
import random

from game_messages import Message
from components.ai import ConfusedMonster

def heal(*args, **kwargs):
    entity = args[0]
    amount = kwargs.get('amount')

    results = []

    if entity.fighter.hp == entity.fighter.max_hp:
        results.append({'consumed': False, 'message': Message('You are already at full health', libtcod.Color(255,228,120))})
    else:
        entity.fighter.heal(amount)
        results.append({'consumed': True, 'message': Message('Your wounds start to feel better!', libtcod.Color(93,222,135))})

    return results

def cast_lightning(*args, **kwargs):
    caster = args[0]
    entities = kwargs.get('entities')
    fov_map = kwargs.get('fov_map')
    damage = kwargs.get('damage')
    maximum_range = kwargs.get('maximum_range')

    results = []

    target = None
    closest_distance = maximum_range + 1

    for entity in entities:
        if entity.fighter and entity != caster and libtcod.map_is_in_fov(fov_map, entity.x, entity.y):
            distance = caster.distance_to(entity)

            if distance < closest_distance:
                target = entity
                closest_distance = distance

    if target:
        #NOTE: this can give coords outside FOV ... (maybe A*?)
        coords = libtcod.los.bresenham((caster.x, caster.y), (target.x, target.y))[1:]
        results.append({'lightning_coords': coords})
        results.append({'consumed': True, 'target': target, 'message': Message('A lighting bolt strikes the {0} with a loud thunder! The damage is {1}.'.format(target.name, damage))})
        results.extend(target.fighter.take_damage(damage))
    else:
        results.append({'consumed': False, 'target': None, 'message': Message('No enemy is close enough to strike.', libtcod.Color(235,86,75))})

    return results

def cast_fireball(*args, **kwargs):
    entities = kwargs.get('entities')
    fov_map = kwargs.get('fov_map')
    damage = kwargs.get('damage')
    radius = kwargs.get('radius')
    target_x = kwargs.get('target_x')
    target_y = kwargs.get('target_y')
    game_map = kwargs.get('game_map')

    results = []

    if not libtcod.map_is_in_fov(fov_map, target_x, target_y):
        results.append({'consumed': False, 'message': Message('You cannot target a tile outside your field of view.', libtcod.Color(255,228,120))})
        return results

    results.append({'consumed': True, 'message': Message('The fireball explodes, burning everything within {0} tiles!'.format(radius), libtcod.Color(242,166,94))})

    coords = []
    for x in range(target_x - radius, target_x + radius + 1):
        for y in range(target_y - radius, target_y + radius + 1):
            if 0 <= x < game_map.width and 0 <= y < game_map.height and math.sqrt((x - target_x) ** 2 + (y - target_y) ** 2) <= radius and not game_map.is_blocked(x, y):
                coords.append((x,y))

    results.append({'explosion_coords': coords})

    for entity in entities:
        if entity.distance(target_x, target_y) <= radius and entity.fighter:
            results.append({'message': Message('The {0} gets burned for {1} hit points.'.format(entity.name, damage), libtcod.Color(242,166,94))})
            results.extend(entity.fighter.take_damage(damage))

    return results

def cast_confuse(*args, **kwargs):
    entities = kwargs.get('entities')
    fov_map = kwargs.get('fov_map')
    target_x = kwargs.get('target_x')
    target_y = kwargs.get('target_y')

    results = []

    if not libtcod.map_is_in_fov(fov_map, target_x, target_y):
        results.append({'consumed': False, 'message': Message('You cannot target a tile outside your field of view.', libtcod.Color(255,228,120))})
        return results

    for entity in entities:
        if entity.x == target_x and entity.y == target_y and entity.ai:
            confused_ai = ConfusedMonster(entity.ai, 10)

            confused_ai.owner = entity
            entity.ai = confused_ai
            entity.is_confused = True
            entity.tiles = [t + 32 for t in entity.tiles]

            results.append({'confused_entity': entity})
            results.append({'consumed': True, 'message': Message('The eyes of the {0} look vacant, as he starts to stumble around!'.format(entity.name), libtcod.Color(93,222,135))})
            break
    else:
        results.append({'consumed': False, 'message': Message('There is no targetable enemy at that location.', libtcod.Color(255,228,120))})

    return results
