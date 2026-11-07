"""Timberborn Save Tool - éditeur local de sauvegardes .timber (Python 3, Tkinter)."""
import copy
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import zipfile
import uuid
import random
import re


CAPACITIES = {
    'SmallPile': 20, 'LargePile': 180, 'UndergroundPile': 1000,
    'SmallIndustrialPile': 20, 'LargeIndustrialPile': 180,
    'SmallWarehouse': 30, 'MediumWarehouse': 200, 'LargeWarehouse': 1200,
    'SmallTank': 30, 'MediumTank': 300, 'LargeTank': 1200,
}


def capacity_for(template):
    return CAPACITIES.get(template.split('.')[0])


def stockpiles(world):
    for entity in world.get('Entities', []):
        components = entity.get('Components', {})
        inventory = components.get('Inventory:Stockpile')
        allower = components.get('SingleGoodAllower', {})
        good = allower.get('AllowedGood')
        capacity = capacity_for(entity.get('Template', ''))
        if not good or not capacity or 'ConstructionSite' in components:
            continue  # un bâtiment encore en construction ne doit jamais être rempli
        if inventory is None:
            # Inventaire absent = stockage construit mais actuellement vide.
            # Le composant sera créé seulement lors du remplissage.
            storage = {'Goods': []}
        elif isinstance(inventory, dict):
            storage = inventory.get('Storage')
            if not isinstance(storage, dict) or not isinstance(storage.get('Goods'), list):
                continue
        else:
            continue
        yield entity, storage, good, capacity


def stock_summary(world):
    from collections import defaultdict
    summary = defaultdict(lambda: [0, 0, 0])
    for _, storage, good, capacity in stockpiles(world):
        amount = sum(max(0, x.get('Amount', 0)) for x in storage['Goods'] if x.get('Good') == good)
        summary[good][0] += 1
        summary[good][1] += amount
        summary[good][2] += capacity
    return dict(sorted(summary.items()))


def fill_stockpiles(world, selected_goods=None):
    """Fill only *assigned* built storage. Do not change construction/production inventories."""
    changed = 0
    for entity, storage, good, capacity in stockpiles(world):
        if selected_goods is not None and good not in selected_goods:
            continue
        # Remove old contents if the building was reassigned to a different good.
        goods = storage['Goods']
        if goods != [{'Good': good, 'Amount': capacity}]:
            entity['Components'].setdefault('Inventory:Stockpile', {'Storage': storage})
            storage['Goods'] = [{'Good': good, 'Amount': capacity}]
            changed += 1
    return changed


def read_save(path):
    with zipfile.ZipFile(path, 'r') as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive ZIP endommagée')
        members = [(item, archive.read(item.filename)) for item in archive.infolist()]
    world_members = [data for info, data in members if info.filename == 'world.json']
    if len(world_members) != 1:
        raise ValueError('Fichier world.json absent ou dupliqué')
    world = json.loads(world_members[0].decode('utf-8-sig'))
    if not isinstance(world, dict) or not isinstance(world.get('Entities'), list):
        raise ValueError('Structure de sauvegarde non reconnue')
    return members, world


def write_save(path, members, world):
    payload = json.dumps(world, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    tmp = path.with_name(path.name + '.tmp')
    try:
        with zipfile.ZipFile(tmp, 'w') as archive:
            for info, raw in members:
                archive.writestr(copy.copy(info), payload if info.filename == 'world.json' else raw)
        with zipfile.ZipFile(tmp) as archive:
            if archive.testzip() is not None:
                raise ValueError('Archive invalide après écriture')
            check = json.loads(archive.read('world.json'))
            if len(check.get('Entities', [])) != len(world['Entities']):
                raise ValueError('Nombre d’entités modifié de manière inattendue')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()




def living_entities(world, kind='beaver'):
    """Entities with a complete in-game template suitable for safe duplication."""
    for ent in world.get('Entities', []):
        template = str(ent.get('Template', ''))
        if kind == 'beaver' and template != 'BeaverAdult':
            continue
        if kind == 'bot' and not (template == 'Bot' or template.startswith('Bot.') or template.startswith('BotAdult')):
            continue
        comps = ent.get('Components', {})
        if isinstance(comps.get('Character'), dict) and comps['Character'].get('Alive', True):
            yield ent


def _unique_clone(source, occupied, index):
    """Copy the entire existing entity, replace its unique ID and self references."""
    clone = copy.deepcopy(source)
    original_id = source['Id']
    new_id = str(uuid.uuid4())
    while new_id in occupied:
        new_id = str(uuid.uuid4())
    occupied.add(new_id)
    clone['Id'] = new_id
    def replace_self(o):
        if isinstance(o, dict):
            for k, v in o.items(): o[k] = replace_self(v)
        elif isinstance(o, list):
            for i, v in enumerate(o): o[i] = replace_self(v)
        elif isinstance(o, str):
            if o == original_id: return new_id
            if o.startswith(original_id + ':'): return new_id + o[len(original_id):]
        return o
    replace_self(clone['Components'])
    comps = clone['Components']
    if 'NamedEntity' in comps and 'EntityName' in comps['NamedEntity']:
        comps['NamedEntity']['EntityName'] = f"{comps['NamedEntity']['EntityName']}-{index:03d}"
    # Position offsets are deliberately kept tiny so actors don't spawn far from paths.
    char = comps['Character']
    if 'Position' in char:
        char['Position']['X'] = round(char['Position']['X'] + ((index % 7) - 3) * 0.04, 5)
        char['Position']['Z'] = round(char['Position']['Z'] + ((index % 9) - 4) * 0.04, 5)
    return clone


def add_characters(world, count, kind='beaver', age_days=15):
    """Clone live adult beavers or existing robots without fabricating components.

    For beavers, both the birth date AND life progress must change, otherwise
    even a visually young beaver can die of old age soon after loading.
    """
    count = int(count)
    if not 1 <= count <= 1000:
        raise ValueError('Choisis de 1 à 1 000 personnages par opération.')
    if kind not in ('beaver', 'bot'):
        raise ValueError('Type de personnage inconnu.')
    candidates = list(living_entities(world, kind))
    if not candidates:
        if kind == 'bot':
            raise ValueError('Aucun robot existant dans cette sauvegarde. Fabrique au moins un Bot en jeu puis sauvegarde : il servira de modèle complet pour les suivants.')
        raise ValueError('Aucun castor adulte existant à dupliquer.')
    now = int(world.get('Singletons', {}).get('DayNightCycle', {}).get('DayNumber', 0))
    age_days = int(age_days)
    if kind == 'beaver' and not 5 <= age_days <= 40:
        raise ValueError('Choisis un âge entre 5 et 40 jours pour les adultes.')
    occupied = {e.get('Id') for e in world['Entities']}
    for i in range(1, count + 1):
        source = candidates[(i-1) % len(candidates)]
        ent = _unique_clone(source, occupied, i)
        cmp = ent['Components']
        if kind == 'beaver':
            char = cmp['Character']
            source_age = max(1, now - int(source['Components']['Character'].get('DayOfBirth', now-15)))
            source_progress = float(source['Components'].get('LifeProgressor', {}).get('LifeProgress', 0.25))
            rate = source_progress / source_age if 0 < source_progress < 2 else (1 / 60)
            rate = max(1/85, min(1/45, rate))
            char['DayOfBirth'] = now - age_days
            if 'LifeProgressor' in cmp:
                cmp['LifeProgressor']['LifeProgress'] = round(age_days * rate, 8)
            if 'BeaverLongevity' in cmp:
                cmp['BeaverLongevity']['ExpectedLongevity'] = max(1.0, float(cmp['BeaverLongevity'].get('ExpectedLongevity', 1.0)))
            if 'NeedManager' in cmp:
                for need in cmp['NeedManager'].get('Needs', []):
                    if need.get('Name') == 'BadwaterContamination':
                        need['Points'] = -1.0
                    elif need.get('Name') in ('Hunger', 'Thirst', 'Sleep'):
                        need['Points'] = max(0.85, float(need.get('Points', 0.0)))
        world['Entities'].append(ent)
    return count



# Limited, explicit editing of settings actually persisted in Timberborn 1.1.
DIFFICULTY_FIELDS = {
    'TemperateWeatherDurationService': ('MinTemperateWeatherDuration', 'MaxTemperateWeatherDuration'),
    'DroughtWeather': ('MinDroughtDuration', 'MaxDroughtDuration'),
    'BadtideWeather': ('MinBadtideWeatherDuration', 'MaxBadtideWeatherDuration'),
}

def difficulty_settings(world):
    ss=world.get('Singletons', {})
    return {key: (int(ss[key][a]), int(ss[key][b])) for key,(a,b) in DIFFICULTY_FIELDS.items()
            if isinstance(ss.get(key),dict) and a in ss[key] and b in ss[key]}

def set_difficulty(world, values):
    for section, (minimum,maximum) in values.items():
        if section not in DIFFICULTY_FIELDS or section not in world['Singletons']:
            raise ValueError('Unsupported difficulty setting')
        a,b=DIFFICULTY_FIELDS[section]
        minimum,maximum=int(minimum),int(maximum)
        if not 0 <= minimum <= maximum <= 365:
            raise ValueError('Durées attendues : 0 à 365 jours, minimum ≤ maximum.')
        world['Singletons'][section][a]=minimum
        world['Singletons'][section][b]=maximum
    return len(values)

def set_science(world, points):
    points=int(points)
    if not 0 <= points <= 2_000_000_000:
        raise ValueError('Science: value must be from 0 to 2,000,000,000.')
    service=world.get('Singletons',{}).get('ScienceService')
    if not isinstance(service,dict) or 'SciencePoints' not in service:
        raise ValueError('ScienceService absent in this save.')
    service['SciencePoints']=points
    return points

def satisfy_beavers(world, hunger=True, thirst=True, sleep=False):
    """Instantaneous refill; does not touch game need progression or global modifiers."""
    names=set()
    if hunger:names.add('Hunger')
    if thirst:names.add('Thirst')
    if sleep:names.add('Sleep')
    count=0
    for ent in world.get('Entities',[]):
        if ent.get('Template') not in ('BeaverAdult','BeaverChild'):continue
        needs=ent.get('Components',{}).get('NeedManager',{}).get('Needs',[])
        for need in needs:
            if need.get('Name') in names:
                need['Points']=1.0
                count+=1
    return count
