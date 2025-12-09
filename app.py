#!/usr/bin/env python3
"""
DF Tales Flask Application
Web interface for Dwarf Fortress legends data.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify, send_file
from PIL import Image
import io

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MASTER_DB_PATH = DATA_DIR / "master.db"
MASTER_SCHEMA_PATH = BASE_DIR / "master_schema.sql"

# Race labels mapping (icon, label)
RACE_DATA = {
    # Civilized races
    'HUMAN': ('☺', 'Human'),
    'DWARF': ('☻', 'Dwarf'),
    'ELF': ('♠', 'Elf'),
    'GOBLIN': ('g', 'Goblin'),
    'KOBOLD': ('k', 'Kobold'),
    # Megabeasts & titans
    'DRAGON': ('D', 'Dragon'),
    'HYDRA': ('H', 'Hydra'),
    'COLOSSUS_BRONZE': ('☼', 'Bronze Colossus'),
    'BIRD_ROC': ('R', 'Roc'),
    # Giants & semi-megabeasts
    'CYCLOPS': ('C', 'Cyclops'),
    'ETTIN': ('E', 'Ettin'),
    'GIANT': ('G', 'Giant'),
    'MINOTAUR': ('M', 'Minotaur'),
    'TROLL': ('T', 'Troll'),
    'OGRE': ('O', 'Ogre'),
    'YETI': ('Y', 'Yeti'),
    # Cave creatures
    'JABBERER': ('J', 'Jabberer'),
    'BLIND_CAVE_OGRE': ('O', 'Blind Cave Ogre'),
    'VORACIOUS_CAVE_CRAWLER': ('v', 'Voracious Cave Crawler'),
    'TROGLODYTE': ('t', 'Troglodyte'),
    'GORLAK': ('g', 'Gorlak'),
    'MOLEMARIAN': ('m', 'Molemarian'),
    'OLM_MAN': ('o', 'Olm Man'),
    'CAVE_FISH_MAN': ('f', 'Cave Fish Man'),
    'PLUMP_HELMET_MAN': ('♣', 'Plump Helmet Man'),
    # Flying creatures
    'HARPY': ('♀', 'Harpy'),
    'NIGHTWING': ('N', 'Nightwing'),
    'BAT_GIANT': ('b', 'Giant Bat'),
    'BIRD_OSPREY': ('○', 'Osprey'),
    'BIRD_WREN': ('○', 'Wren'),
    'HUNGRY_HEAD': ('☼', 'Hungry Head'),
    'SPIDER_CAVE_GIANT': ('§', 'Giant Cave Spider'),
    # Big cats
    'LION': ('♌', 'Lion'),
    'LEOPARD': ('♌', 'Leopard'),
    'CHEETAH': ('♌', 'Cheetah'),
    'JAGUAR': ('♌', 'Jaguar'),
    'COUGAR': ('♌', 'Cougar'),
    'GIANT_LION': ('♌', 'Giant Lion'),
    'GIANT_LEOPARD': ('♌', 'Giant Leopard'),
    'GIANT_CHEETAH': ('♌', 'Giant Cheetah'),
    'GIANT_JAGUAR': ('♌', 'Giant Jaguar'),
    'GIANT_COUGAR': ('♌', 'Giant Cougar'),
    # Canines
    'WOLF': ('w', 'Wolf'),
    'DINGO': ('d', 'Dingo'),
    'GIANT_WOLF': ('W', 'Giant Wolf'),
    'GIANT_DINGO': ('D', 'Giant Dingo'),
    # Bears
    'BEAR_GRIZZLY': ('B', 'Grizzly Bear'),
    'BEAR_BLACK': ('B', 'Black Bear'),
    'BEAR_POLAR': ('B', 'Polar Bear'),
    'GIANT_BEAR_GRIZZLY': ('B', 'Giant Grizzly Bear'),
    'GIANT_BEAR_BLACK': ('B', 'Giant Black Bear'),
    'GIANT_BEAR_POLAR': ('B', 'Giant Polar Bear'),
    # Reptiles
    'ANACONDA': ('S', 'Anaconda'),
    'CROCODILE_SALTWATER': ('~', 'Saltwater Crocodile'),
    'ALLIGATOR': ('~', 'Alligator'),
    'GIANT_ANACONDA': ('S', 'Giant Anaconda'),
    'GIANT_CROCODILE_SALTWATER': ('~', 'Giant Saltwater Crocodile'),
    'GIANT_ALLIGATOR': ('~', 'Giant Alligator'),
    # Other
    'HYENA': ('h', 'Hyena'),
    'GIANT_HYENA': ('H', 'Giant Hyena'),
    'GOAT_MOUNTAIN': ('g', 'Mountain Goat'),
    'TERMITE': ('·', 'Termite'),
    # Animal people
    'LION_MAN': ('☺', 'Lion Man'),
    'LEOPARD_MAN': ('☺', 'Leopard Man'),
    'CHEETAH_MAN': ('☺', 'Cheetah Man'),
    'JAGUAR_MAN': ('☺', 'Jaguar Man'),
    'COUGAR_MAN': ('☺', 'Cougar Man'),
    'WOLF_MAN': ('☺', 'Wolf Man'),
    'DINGO_MAN': ('☺', 'Dingo Man'),
    'TIGER_MAN': ('☺', 'Tiger Man'),
    'ALLIGATOR_MAN': ('☺', 'Alligator Man'),
    'ANACONDA_MAN': ('☺', 'Anaconda Man'),
    'CROCODILE_SALTWATER_MAN': ('☺', 'Saltwater Crocodile Man'),
    'BEAR_BLACK_MAN': ('☺', 'Black Bear Man'),
    'BEAR_POLAR_MAN': ('☺', 'Polar Bear Man'),
    'EAGLE_MAN': ('☺', 'Eagle Man'),
    'AARDVARK_MAN': ('☺', 'Aardvark Man'),
    'SERPENT_MAN': ('☺', 'Serpent Man'),
    'AMPHIBIAN_MAN': ('☺', 'Amphibian Man'),
    'REPTILE_MAN': ('☺', 'Reptile Man'),
    'RAT_MAN': ('r', 'Rat Man'),
    'MOSQUITO_MAN': ('☺', 'Mosquito Man'),
    'RHINOCEROS_MAN': ('☺', 'Rhinoceros Man'),
    'WEASEL_MAN': ('☺', 'Weasel Man'),
    'BOBCAT_MAN': ('☺', 'Bobcat Man'),
    'HEDGEHOG_MAN': ('☺', 'Hedgehog Man'),
    'PORCUPINE_MAN': ('☺', 'Porcupine Man'),
    'IBEX_MAN': ('☺', 'Ibex Man'),
    'GREAT_HORNED_OWL_MAN': ('☺', 'Great Horned Owl Man'),
    'CARDINAL_MAN': ('☺', 'Cardinal Man'),
    'BLUEJAY_MAN': ('☺', 'Bluejay Man'),
    'KESTREL_MAN': ('☺', 'Kestrel Man'),
    'JUMPING_SPIDER_MAN': ('☺', 'Jumping Spider Man'),
    'GOAT_MOUNTAIN_MAN': ('☺', 'Mountain Goat Man'),
    'CAPYBARA MAN': ('☺', 'Capybara Man'),
    'HONEY BADGER MAN': ('☺', 'Honey Badger Man'),
    'PEREGRINE FALCON MAN': ('☺', 'Peregrine Falcon Man'),
    'KIWI MAN': ('☺', 'Kiwi Man'),
    'MOOSE MAN': ('☺', 'Moose Man'),
    'OSTRICH MAN': ('☺', 'Ostrich Man'),
    'FOX_MAN': ('☺', 'Fox Man'),
    'HAMSTER_MAN': ('☺', 'Hamster Man'),
    'KOALA_MAN': ('☺', 'Koala Man'),
    'LYNX_MAN': ('☺', 'Lynx Man'),
    'MACAQUE_RHESUS_MAN': ('☺', 'Rhesus Macaque Man'),
    'MARMOT_HOARY_MAN': ('☺', 'Hoary Marmot Man'),
    'PARAKEET_MAN': ('☺', 'Parakeet Man'),
    'SKINK_MAN': ('☺', 'Skink Man'),
    'STOAT_MAN': ('☺', 'Stoat Man'),
    'WREN_MAN': ('☺', 'Wren Man'),
    'BUSHTIT_MAN': ('☺', 'Bushtit Man'),
    'BUZZARD_MAN': ('☺', 'Buzzard Man'),
    'CHAMELEON_MAN': ('☺', 'Chameleon Man'),
    'COCKATIEL_MAN': ('☺', 'Cockatiel Man'),
    'COYOTE_MAN': ('☺', 'Coyote Man'),
    'RW_BLACKBIRD_MAN': ('☺', 'Blackbird Man'),
}

# Pattern-based icons
RACE_PATTERNS = {
    'FORGOTTEN_BEAST': ('Ω', 'Forgotten Beast'),
    'NIGHT_CREATURE': ('N', 'Night Creature'),
    'DEMON': ('&', 'Demon'),
    'TITAN': ('Θ', 'Titan'),
    'HFEXP': ('?', 'Experiment'),
}

# Race icons directory
RACE_ICONS_DIR = BASE_DIR / "static" / "icons" / "races"

# Site type labels mapping (icon, label)
SITE_TYPE_DATA = {
    'camp': ('⌂', 'Camp'),
    'castle': ('♜', 'Castle'),
    'cave': ('○', 'Cave'),
    'dark fortress': ('▓', 'Dark Fortress'),
    'dark pits': ('▼', 'Dark Pits'),
    'forest retreat': ('♣', 'Forest Retreat'),
    'fort': ('⌂', 'Fort'),
    'fortress': ('☼', 'Fortress'),
    'hamlet': ('∩', 'Hamlet'),
    'hillocks': ('▲', 'Hillocks'),
    'labyrinth': ('▒', 'Labyrinth'),
    'lair': ('◘', 'Lair'),
    'monastery': ('†', 'Monastery'),
    'mountain halls': ('▲', 'Mountain Halls'),
    'mysterious dungeon': ('▒', 'Mysterious Dungeon'),
    'mysterious lair': ('◘', 'Mysterious Lair'),
    'mysterious palace': ('♔', 'Mysterious Palace'),
    'shrine': ('†', 'Shrine'),
    'tomb': ('☠', 'Tomb'),
    'tower': ('♜', 'Tower'),
    'town': ('⌂', 'Town'),
    'vault': ('■', 'Vault'),
}

# Site icons directory
SITE_ICONS_DIR = BASE_DIR / "static" / "icons" / "sites"

# Structure type labels mapping (icon, label)
STRUCTURE_TYPE_DATA = {
    'counting_house': ('$', 'Counting House'),
    'dungeon': ('▓', 'Dungeon'),
    'guildhall': ('☼', 'Guildhall'),
    'inn_tavern': ('☺', 'Inn/Tavern'),
    'keep': ('♜', 'Keep'),
    'library': ('▒', 'Library'),
    'market': ('○', 'Market'),
    'mead_hall': ('▓', 'Mead Hall'),
    'temple': ('†', 'Temple'),
    'tomb': ('☠', 'Tomb'),
    'tower': ('♜', 'Tower'),
    'underworld_spire': ('▼', 'Underworld Spire'),
}

# Structure icons directory
STRUCTURE_ICONS_DIR = BASE_DIR / "static" / "icons" / "structures"

# Artifact type labels mapping (icon, label)
ARTIFACT_TYPE_DATA = {
    'book': ('📖', 'Book'),
    'tool': ('⚒', 'Tool'),
    'weapon': ('⚔', 'Weapon'),
    'earring': ('○', 'Earring'),
    'totem': ('☠', 'Totem'),
    'ring': ('○', 'Ring'),
    'scepter': ('♔', 'Scepter'),
    'amulet': ('◊', 'Amulet'),
    'pants': ('▬', 'Pants'),
    'slab': ('▬', 'Slab'),
    'figurine': ('♦', 'Figurine'),
    'shield': ('◘', 'Shield'),
    'armor': ('☼', 'Armor'),
    'bracelet': ('○', 'Bracelet'),
    'crown': ('♔', 'Crown'),
    'gem': ('◆', 'Gem'),
    'instrument': ('♪', 'Instrument'),
    'shoes': ('▬', 'Shoes'),
    'toy': ('♦', 'Toy'),
    'helm': ('◘', 'Helm'),
    'trapcomp': ('☼', 'Trap Component'),
    'gloves': ('▬', 'Gloves'),
    'goblet': ('u', 'Goblet'),
    'weaponrack': ('╦', 'Weapon Rack'),
    'chain': ('~', 'Chain'),
    'bin': ('▒', 'Bin'),
    'cage': ('▒', 'Cage'),
    'door': ('▬', 'Door'),
    'armorstand': ('╦', 'Armor Stand'),
    'box': ('▒', 'Box'),
    'floodgate': ('▬', 'Floodgate'),
    'grate': ('▒', 'Grate'),
    'table': ('▬', 'Table'),
    'animaltrap': ('▒', 'Animal Trap'),
    'cabinet': ('▒', 'Cabinet'),
    'chair': ('▬', 'Chair'),
    'coffin': ('▒', 'Coffin'),
    'statue': ('☼', 'Statue'),
}

# Artifact icons directory
ARTIFACT_ICONS_DIR = BASE_DIR / "static" / "icons" / "artifacts"

# Material colors - specific materials mapped to colors
MATERIAL_COLORS = {
    # Metals - warm metallic colors
    'copper': '#b87333',
    'iron': '#a19d94',
    'steel': '#71797E',
    'silver': '#c0c0c0',
    'gold': '#ffd700',
    'bronze': '#cd7f32',
    'bismuth bronze': '#cd7f32',
    'brass': '#b5a642',
    'platinum': '#e5e4e2',
    'electrum': '#cfc87c',
    'aluminum': '#848789',
    'native aluminum': '#848789',
    'native silver': '#c0c0c0',
    'native gold': '#ffd700',
    'native platinum': '#e5e4e2',
    'rose gold': '#b76e79',
    'white gold': '#f5f5dc',
    'pig iron': '#6e6e6e',
    'cast iron': '#4a4a4a',
    'billon': '#9a9a7f',
    'black bronze': '#4a3728',
    'lay pewter': '#8a8a8a',
    'trifle pewter': '#9a9a9a',
    'fine pewter': '#aaaaaa',
    'sterling silver': '#bfbfbf',
    # Gems - vibrant colors
    'ruby': '#e0115f',
    'emerald': '#50c878',
    'sapphire': '#0f52ba',
    'diamond': '#b9f2ff',
    'black diamond': '#3b3b3b',
    'blue diamond': '#4169e1',
    'red diamond': '#ff3333',
    'yellow diamond': '#fff44f',
    'clear diamond': '#f0f8ff',
    'amethyst': '#9966cc',
    'topaz': '#ffc87c',
    'aquamarine': '#7fffd4',
    'garnet': '#733635',
    'blue garnet': '#4169e1',
    'opal': '#a8c3bc',
    'fire opal': '#e95c20',
    'precious fire opal': '#ff4500',
    'black opal': '#1c1c1c',
    'white opal': '#f5f5f5',
    'shell opal': '#fff5ee',
    'wax opal': '#f5deb3',
    'jasper opal': '#d2691e',
    'amber opal': '#ffbf00',
    'bone opal': '#e3dac9',
    'bandfire opal': '#ff6347',
    'pearl': '#fdeef4',
    'jade': '#00a86b',
    'blue jade': '#4682b4',
    'alexandrite': '#008b8b',
    'tanzanite': '#4169e1',
    'tourmaline': '#86c67c',
    'spinel': '#ff1493',
    'zircon': '#f0e68c',
    'yellow zircon': '#f4c430',
    'brown zircon': '#8b4513',
    'black zircon': '#2f2f2f',
    'peridot': '#e6e200',
    'citrine': '#e4d00a',
    'morganite': '#f4a7b9',
    'almandine': '#7b1113',
    'pyrope': '#cc0066',
    'black pyrope': '#330033',
    'grossular': '#a8d8a8',
    'cinnamon grossular': '#d2691e',
    'tsavorite': '#00ff7f',
    'bloodstone': '#3b5323',
    # Stone - gray/brown earth tones
    'granite': '#696969',
    'marble': '#f5f5f5',
    'obsidian': '#3d3d3d',
    'basalt': '#4a4a4a',
    'sandstone': '#c2b280',
    'limestone': '#d3c9a1',
    'slate': '#708090',
    'shale': '#5d5d5d',
    'chalk': '#f5f5f5',
    'diorite': '#808080',
    'gneiss': '#6b6b6b',
    'quartzite': '#f5f5f5',
    'andesite': '#9a9a9a',
    'phyllite': '#5f5f5f',
    'mudstone': '#8b7765',
    'gabbro': '#545454',
    'rhyolite': '#9b8b7a',
    'schist': '#6a6a6a',
    'kimberlite': '#5a5a5a',
    'puddingstone': '#8b6b5c',
    # Wood - brown tones
    'oak wood': '#806517',
    'pine wood': '#c19a6b',
    'birch wood': '#f5deb3',
    'maple wood': '#c04000',
    'willow wood': '#9acd32',
    'cedar wood': '#a0522d',
    'mahogany wood': '#c04000',
    'ebony wood': '#3d3d3d',
    # Bone/Ivory - off-white
    'bone': '#e3dac9',
    'ivory': '#fffff0',
    'horn': '#d2b48c',
    'shell': '#fff5ee',
    # Leather/Parchment - tan/brown
    'leather': '#8b4513',
    # Glass/Ceramic
    'glass': '#add8e6',
    'clear glass': '#e0ffff',
    'green glass': '#98fb98',
    'crystal glass': '#f0f8ff',
    'porcelain': '#f5f5f5',
    # Minerals/Ores
    'coal': '#2f2f2f',
    'bituminous coal': '#3d3d3d',
    'lignite': '#4a3728',
    'hematite': '#8b0000',
    'magnetite': '#2f2f2f',
    'malachite': '#0bda51',
    'azurite': '#007fff',
    'galena': '#8a8a8a',
    'sphalerite': '#c4a35a',
    'cinnabar': '#e34234',
    'cobaltite': '#0047ab',
    'tetrahedrite': '#4a4a4a',
    'garnierite': '#00a86b',
    'chromite': '#3d3d3d',
    'realgar': '#ff4500',
    'orpiment': '#ffd700',
    'stibnite': '#6a6a6a',
    'bismuthinite': '#8a8a8a',
    'bauxite': '#c04000',
    # Other minerals
    'calcite': '#f5f5dc',
    'gypsum': '#f8f8ff',
    'alabaster': '#f2f0e6',
    'saltpeter': '#f5f5f5',
    'borax': '#f5f5f5',
    'alunite': '#f0e68c',
    'satinspar': '#fffaf0',
    'mica': '#c4aead',
    'primal salt': '#ffd1dc',
    'brimstone': '#ffff00',
    # Creature materials (default tan for parchment)
}

# Material category patterns for fallback colors
MATERIAL_CATEGORY_PATTERNS = [
    ('parchment', '#d4a574'),  # Tan/beige for all parchment
    ('wood', '#8b5a2b'),       # Brown for wood
    ('bone', '#e3dac9'),       # Off-white for bone
    ('leather', '#8b4513'),    # Brown for leather
    ('silk', '#fffaf0'),       # Off-white for silk
    ('cloth', '#dcdcdc'),      # Gray for cloth
    ('wool', '#f5f5dc'),       # Beige for wool
    ('glaze', '#add8e6'),      # Light blue for glazes
    ('glass', '#add8e6'),      # Light blue for glass
    ('opal', '#a8c3bc'),       # Opalescent for opals
    ('agate', '#b5651d'),      # Brown for agates
    ('jasper', '#d2691e'),     # Orange-brown for jasper
]


def get_material_color(material):
    """Get color for a material."""
    if not material:
        return None

    mat_lower = material.lower()

    # Check direct mapping first
    if mat_lower in MATERIAL_COLORS:
        return MATERIAL_COLORS[mat_lower]

    # Check category patterns
    for pattern, color in MATERIAL_CATEGORY_PATTERNS:
        if pattern in mat_lower:
            return color

    return None


# Event type labels mapping (icon, label)
EVENT_TYPE_DATA = {
    'add_hf_entity_link': ('⚭', 'Joined Entity'),
    'add_hf_hf_link': ('♥', 'Relationship Formed'),
    'add_hf_site_link': ('⌂', 'Site Link Added'),
    'artifact_created': ('★', 'Artifact Created'),
    'assume_identity': ('?', 'Identity Assumed'),
    'body_abused': ('†', 'Body Abused'),
    'change_creature_type': ('∞', 'Creature Changed'),
    'change_hf_job': ('☼', 'Job Changed'),
    'change_hf_state': ('→', 'State Changed'),
    'create_entity_position': ('♔', 'Position Created'),
    'created_building': ('⌂', 'Building Created'),
    'creature_devoured': ('☠', 'Creature Devoured'),
    'entity_action': ('!', 'Entity Action'),
    'hf_act_on_building': ('⌂', 'Building Action'),
    'hf_does_interaction': ('✧', 'Interaction'),
    'hf_learns_secret': ('?', 'Secret Learned'),
    'hist_figure_died': ('☠', 'Death'),
    'hist_figure_new_pet': ('♦', 'New Pet'),
    'hist_figure_wounded': ('†', 'Wounded'),
    'item_stolen': ('!', 'Item Stolen'),
    'remove_hf_entity_link': ('⚭', 'Left Entity'),
    'remove_hf_site_link': ('⌂', 'Site Link Removed'),
    'replaced_building': ('⌂', 'Building Replaced'),
    'war_peace_accepted': ('☮', 'Peace Accepted'),
    'war_peace_rejected': ('⚔', 'Peace Rejected'),
}


def get_artifact_type_info(artifact_type, artifact_subtype=None):
    """Get artifact type label, text icon, and image icon path."""
    if not artifact_type:
        return {'label': '-', 'icon': '·', 'img': None}

    icon = '·'
    label = None
    img = None

    # Special handling for written content containers (scrolls use book icon)
    if artifact_subtype and artifact_subtype.lower() in ('scroll', 'quire', 'codex'):
        img = '/static/icons/artifacts/book.png'
        label = artifact_subtype.replace('_', ' ').title()
        return {'label': label, 'icon': '📜', 'img': img}

    # Check for image icon
    for ext in ['.png', '.gif']:
        icon_path = ARTIFACT_ICONS_DIR / f"{artifact_type}{ext}"
        if icon_path.exists():
            img = f'/static/icons/artifacts/{artifact_type}{ext}'
            break

    # Check direct mapping
    if artifact_type in ARTIFACT_TYPE_DATA:
        icon, label = ARTIFACT_TYPE_DATA[artifact_type]

    # Default: title case
    if label is None:
        label = artifact_type.replace('_', ' ').title()

    return {'label': label, 'icon': icon, 'img': img}


def get_event_type_info(event_type):
    """Get event type label and icon."""
    if not event_type:
        return {'label': '-', 'icon': '·'}

    icon = '·'
    label = None

    # Normalize: convert spaces to underscores for lookup
    normalized = event_type.replace(' ', '_')

    # Check direct mapping (with normalized key)
    if normalized in EVENT_TYPE_DATA:
        icon, label = EVENT_TYPE_DATA[normalized]

    # Default: title case (use original with spaces replaced)
    if label is None:
        label = event_type.replace('_', ' ').title()

    return {'label': label, 'icon': icon}


def format_event_type(event_type):
    """Convert event type to readable label with icon."""
    info = get_event_type_info(event_type)
    if info['label'] == '-':
        return '-'
    return f"{info['icon']} {info['label']}"


def format_event_details(event):
    """Format event details into a human-readable description."""
    import json
    from markupsafe import Markup

    event_type = event['type'] or ''
    normalized_type = event_type.replace(' ', '_')

    parts = []

    # Parse extra_data if present
    extra = {}
    if event['extra_data']:
        try:
            extra = json.loads(event['extra_data'])
        except:
            pass

    # Get values from event or extra_data
    hfid = event['hfid'] or extra.get('hfid') or extra.get('histfig') or extra.get('hist_figure_id')
    site_id = event['site_id'] or extra.get('site_id')
    civ_id = event['civ_id'] or extra.get('civ_id') or extra.get('civ')
    entity_id = event['entity_id'] or extra.get('entity_id')

    # Build description based on event type
    if normalized_type == 'add_hf_site_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            if link_type == 'lair':
                parts.append(f"HF#{hfid} established a lair at Site#{site_id}")
            elif link_type == 'home_site_realization_building':
                parts.append(f"HF#{hfid} moved into building at Site#{site_id}")
            elif link_type == 'seat_of_power':
                parts.append(f"HF#{hfid} claimed seat of power at Site#{site_id}")
            elif link_type == 'occupation':
                parts.append(f"HF#{hfid} occupied Site#{site_id}")
            elif link_type == 'home_site_abstract_building':
                parts.append(f"HF#{hfid} took residence at Site#{site_id}")
            elif link_type == 'hangout':
                parts.append(f"HF#{hfid} started hanging out at Site#{site_id}")
            else:
                parts.append(f"HF#{hfid} linked to Site#{site_id} ({link_type.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>Site#{site_id}</span>")

    elif normalized_type == 'remove_hf_site_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            parts.append(f"HF#{hfid} left Site#{site_id} ({link_type.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>Site#{site_id}</span>")

    elif normalized_type == 'add_hf_entity_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            if link_type == 'member':
                parts.append(f"HF#{hfid} joined Entity#{civ_id}")
            elif link_type == 'position':
                position = extra.get('position', 'a position')
                parts.append(f"HF#{hfid} took {position} in Entity#{civ_id}")
            elif link_type == 'former member':
                parts.append(f"HF#{hfid} was former member of Entity#{civ_id}")
            elif link_type == 'prisoner':
                parts.append(f"HF#{hfid} imprisoned by Entity#{civ_id}")
            elif link_type == 'enemy':
                parts.append(f"HF#{hfid} became enemy of Entity#{civ_id}")
            elif link_type == 'slave':
                parts.append(f"HF#{hfid} enslaved by Entity#{civ_id}")
            else:
                parts.append(f"HF#{hfid} linked to Entity#{civ_id} ({link_type.replace('_', ' ')})")
        elif civ_id:
            parts.append(f"<span class='detail-limited'>Entity#{civ_id}</span>")

    elif normalized_type == 'remove_hf_entity_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            parts.append(f"HF#{hfid} left Entity#{civ_id} ({link_type.replace('_', ' ')})")
        elif civ_id:
            parts.append(f"<span class='detail-limited'>Entity#{civ_id}</span>")

    elif normalized_type == 'hist_figure_died':
        cause = event['death_cause'] or extra.get('death_cause')
        slayer = event['slayer_hfid'] or extra.get('slayer_hfid')
        if hfid:
            if slayer:
                parts.append(f"HF#{hfid} killed by HF#{slayer}")
            else:
                parts.append(f"HF#{hfid} died")
            if cause:
                parts.append(f"({cause.replace('_', ' ')})")
            if site_id:
                parts.append(f"at Site#{site_id}")
        elif site_id:
            parts.append(f"<span class='detail-limited'>Site#{site_id}</span>")

    elif normalized_type == 'add_hf_hf_link':
        hfid1 = extra.get('hfid1') or extra.get('hf') or hfid
        hfid2 = extra.get('hfid2') or extra.get('hf_target')
        link_type = extra.get('link_type')
        if hfid1 and hfid2:
            rel = link_type.replace('_', ' ') if link_type else 'relationship'
            parts.append(f"HF#{hfid1} and HF#{hfid2} formed {rel}")
        else:
            parts.append("<span class='detail-limited'>-</span>")

    elif normalized_type == 'artifact_created':
        artifact_id = event['artifact_id'] or extra.get('artifact_id')
        if hfid and artifact_id:
            parts.append(f"HF#{hfid} created Artifact#{artifact_id}")
            if site_id:
                parts.append(f"at Site#{site_id}")
        elif artifact_id:
            parts.append(f"Artifact#{artifact_id} created")
            if site_id:
                parts.append(f"at Site#{site_id}")
        else:
            parts.append("<span class='detail-limited'>-</span>")

    elif normalized_type == 'change_hf_state':
        state = event['state'] or extra.get('state')
        reason = event['reason'] or extra.get('reason')
        if hfid and state:
            parts.append(f"HF#{hfid} became {state.replace('_', ' ')}")
            if site_id:
                parts.append(f"at Site#{site_id}")
            if reason:
                parts.append(f"({reason.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>Site#{site_id}</span>")

    elif normalized_type == 'change_hf_job':
        new_job = extra.get('new_job')
        old_job = extra.get('old_job')
        if hfid and new_job:
            if old_job:
                parts.append(f"HF#{hfid} changed from {old_job.replace('_', ' ')} to {new_job.replace('_', ' ')}")
            else:
                parts.append(f"HF#{hfid} became {new_job.replace('_', ' ')}")
            if site_id:
                parts.append(f"at Site#{site_id}")
        elif site_id:
            parts.append(f"<span class='detail-limited'>Site#{site_id}</span>")

    elif normalized_type == 'created_site':
        site_civ_id = extra.get('site_civ_id')
        if civ_id and site_id:
            parts.append(f"Entity#{civ_id} founded Site#{site_id}")
        elif site_id:
            parts.append(f"Site#{site_id} founded")

    elif normalized_type == 'created_building' or normalized_type == 'created_structure':
        structure_id = event['structure_id'] or extra.get('structure_id')
        if hfid and structure_id:
            parts.append(f"HF#{hfid} built Structure#{structure_id}")
        elif structure_id:
            parts.append(f"Structure#{structure_id} built")
        if site_id:
            parts.append(f"at Site#{site_id}")

    elif normalized_type == 'hf_destroyed_site':
        if hfid and site_id:
            parts.append(f"HF#{hfid} destroyed Site#{site_id}")
        elif site_id:
            parts.append(f"Site#{site_id} destroyed")

    elif normalized_type == 'hf_attacked_site':
        if hfid and site_id:
            parts.append(f"HF#{hfid} attacked Site#{site_id}")
        elif site_id:
            parts.append(f"Site#{site_id} attacked")

    else:
        # Generic fallback - show available IDs
        shown = []
        if hfid:
            shown.append(f"HF#{hfid}")
        if site_id:
            shown.append(f"Site#{site_id}")
        if civ_id:
            shown.append(f"Civ#{civ_id}")
        if entity_id:
            shown.append(f"Entity#{entity_id}")
        # Show any interesting extra data
        for key in ['link_type', 'state', 'reason', 'cause', 'interaction']:
            if key in extra and extra[key]:
                val = str(extra[key]).replace('_', ' ')
                shown.append(f"{key}: {val}")

        if shown:
            parts.append(', '.join(shown))
        else:
            parts.append('-')

    return Markup(' '.join(parts) if parts else '-')


def get_structure_type_info(struct_type):
    """Get structure type label, text icon, and image icon path."""
    if not struct_type:
        return {'label': '-', 'icon': '·', 'img': None}

    icon = '·'
    label = None
    img = None

    # Check for image icon
    for ext in ['.png', '.gif']:
        icon_path = STRUCTURE_ICONS_DIR / f"{struct_type}{ext}"
        if icon_path.exists():
            img = f'/static/icons/structures/{struct_type}{ext}'
            break

    # Check direct mapping
    if struct_type in STRUCTURE_TYPE_DATA:
        icon, label = STRUCTURE_TYPE_DATA[struct_type]

    # Default: replace underscores and title case
    if label is None:
        label = struct_type.replace('_', ' ').title()

    return {'label': label, 'icon': icon, 'img': img}


def get_site_type_info(site_type):
    """Get site type label, text icon, and image icon path."""
    if not site_type:
        return {'label': '-', 'icon': '·', 'img': None}

    icon = '·'
    label = None
    img = None

    # Check for image icon
    for ext in ['.png', '.gif']:
        icon_path = SITE_ICONS_DIR / f"{site_type.replace(' ', '_')}{ext}"
        if icon_path.exists():
            img = f'/static/icons/sites/{site_type.replace(" ", "_")}{ext}'
            break

    # Check direct mapping
    if site_type in SITE_TYPE_DATA:
        icon, label = SITE_TYPE_DATA[site_type]

    # Default: title case
    if label is None:
        label = site_type.title()

    return {'label': label, 'icon': icon, 'img': img}


def format_site_type(site_type, with_icon=True):
    """Convert site type to readable label with optional icon."""
    info = get_site_type_info(site_type)
    if info['label'] == '-':
        return '-'
    if with_icon:
        return f"{info['icon']} {info['label']}"
    return info['label']


def get_race_info(race, caste=None):
    """Get race label, text icon, and image icon path."""
    if not race:
        return {'label': '-', 'icon': '·', 'img': None}

    icon = '·'
    label = None
    img = None

    # Check for sex-specific icon based on caste (MALE/FEMALE)
    if caste:
        caste_upper = caste.upper() if isinstance(caste, str) else None
        if caste_upper == 'MALE':
            sex_suffix = 'M'
        elif caste_upper == 'FEMALE':
            sex_suffix = 'F'
        else:
            sex_suffix = None

        if sex_suffix:
            for ext in ['.png', '.gif']:
                icon_path = RACE_ICONS_DIR / f"{race}_{sex_suffix}{ext}"
                if icon_path.exists():
                    img = f'/static/icons/races/{race}_{sex_suffix}{ext}'
                    break

    # Fall back to generic race icon
    if img is None:
        for ext in ['.png', '.gif']:
            icon_path = RACE_ICONS_DIR / f"{race}{ext}"
            if icon_path.exists():
                img = f'/static/icons/races/{race}{ext}'
                break

    # If no exact match, check pattern-based icons
    if img is None:
        for pattern in RACE_PATTERNS.keys():
            if race.startswith(pattern):
                for ext in ['.png', '.gif']:
                    icon_path = RACE_ICONS_DIR / f"{pattern}{ext}"
                    if icon_path.exists():
                        img = f'/static/icons/races/{pattern}{ext}'
                        break
                break

    # Check direct mapping
    if race in RACE_DATA:
        icon, label = RACE_DATA[race]
    else:
        # Handle patterns
        for pattern, (pat_icon, pat_label) in RACE_PATTERNS.items():
            if race.startswith(pattern):
                icon, label = pat_icon, pat_label
                break

    # Try to get creature name from database (for procedural creatures like NIGHT_CREATURE_1)
    if label is None or label.startswith('Night Creature'):
        try:
            db = get_db()
            if db:
                creature = db.execute(
                    "SELECT name_singular FROM creatures WHERE creature_id = ?", [race]
                ).fetchone()
                if creature and creature['name_singular']:
                    label = creature['name_singular'].title()
        except:
            pass

    # Default: replace underscores and title case
    if label is None:
        label = race.replace('_', ' ').title()

    return {'label': label, 'icon': icon, 'img': img}


def format_race(race, with_icon=True):
    """Convert race ID to readable label with optional icon."""
    info = get_race_info(race)
    if info['label'] == '-':
        return '-'
    if with_icon:
        return f"{info['icon']} {info['label']}"
    return info['label']

app = Flask(__name__)
app.secret_key = 'df-tales-secret-key'

# Register template filters
app.jinja_env.filters['race_label'] = format_race
app.jinja_env.filters['site_type_label'] = format_site_type
app.jinja_env.filters['event_type_label'] = format_event_type
app.jinja_env.globals['get_race_info'] = get_race_info
app.jinja_env.globals['get_site_type_info'] = get_site_type_info
app.jinja_env.globals['get_artifact_type_info'] = get_artifact_type_info
app.jinja_env.globals['get_material_color'] = get_material_color
app.jinja_env.globals['get_event_type_info'] = get_event_type_info
app.jinja_env.globals['format_event_details'] = format_event_details

# Written content type colors
WRITTEN_TYPE_COLORS = {
    'Poem': '#f0a0f0',           # Pink/lavender
    'MusicalComposition': '#ffd700',  # Gold
    'Manual': '#87ceeb',         # Sky blue
    'Essay': '#98fb98',          # Pale green
    'Choreography': '#ff69b4',   # Hot pink
    'Guide': '#20b2aa',          # Light sea green
    'StarChart': '#e6e6fa',      # Lavender
    'Novel': '#deb887',          # Burlywood
    'ShortStory': '#d2b48c',     # Tan
    'Letter': '#f5f5dc',         # Beige
    'Chronicle': '#bc8f8f',      # Rosy brown
    'CulturalComparison': '#8fbc8f',  # Dark sea green
    'CulturalHistory': '#9acd32',     # Yellow green
    'Dictionary': '#b0c4de',     # Light steel blue
    'Biography': '#dda0dd',      # Plum
    'Autobiography': '#da70d6',  # Orchid
    'ComparativeBiography': '#ee82ee',  # Violet
    'Play': '#ffa07a',           # Light salmon
    'TreatiseOnTechnologicalEvolution': '#40e0d0',  # Turquoise
    'Dialog': '#f0e68c',         # Khaki
    'AlternateHistory': '#cd853f',    # Peru
    'Encyclopedia': '#4682b4',   # Steel blue
}

def get_written_type_info(wtype):
    """Get written content type info with color."""
    if not wtype:
        return {'label': '-', 'color': None, 'img': None}

    label = wtype.replace('_', ' ')
    color = WRITTEN_TYPE_COLORS.get(wtype)

    # Check for icon
    icon_path = Path('static/icons/written') / f"{wtype}.png"
    img = f'/static/icons/written/{wtype}.png' if icon_path.exists() else None

    return {'label': label, 'color': color, 'img': img}

app.jinja_env.globals['get_written_type_info'] = get_written_type_info


def get_master_db():
    """Get master database connection."""
    if 'master_db' not in g:
        DATA_DIR.mkdir(exist_ok=True)
        g.master_db = sqlite3.connect(MASTER_DB_PATH)
        g.master_db.row_factory = sqlite3.Row
        # Initialize schema if needed
        with open(MASTER_SCHEMA_PATH) as f:
            g.master_db.executescript(f.read())
        # Migration: add has_plus and has_map columns if they don't exist
        cursor = g.master_db.cursor()
        cursor.execute("PRAGMA table_info(worlds)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'has_plus' not in columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN has_plus INTEGER DEFAULT 0")
            g.master_db.commit()
        if 'has_map' not in columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN has_map INTEGER DEFAULT 0")
            g.master_db.commit()
    return g.master_db


def get_current_world():
    """Get the current active world from master database."""
    db = get_master_db()
    row = db.execute("SELECT * FROM worlds WHERE is_current = 1").fetchone()
    return dict(row) if row else None


def get_all_worlds():
    """Get all available worlds from master database."""
    db = get_master_db()
    rows = db.execute("SELECT * FROM worlds ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_db():
    """Get database connection for current world."""
    if 'db' not in g:
        world = get_current_world()
        if world and Path(world['db_path']).exists():
            g.db = sqlite3.connect(world['db_path'])
            g.db.row_factory = sqlite3.Row
        else:
            g.db = None
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connections at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
    master_db = g.pop('master_db', None)
    if master_db is not None:
        master_db.close()


def get_stats():
    """Get database statistics."""
    db = get_db()
    if not db:
        return None

    stats = {}
    tables = [
        ('regions', 'Regions'),
        ('sites', 'Sites'),
        ('historical_figures', 'Historical Figures'),
        ('entities', 'Entities'),
        ('artifacts', 'Artifacts'),
        ('historical_events', 'Events'),
        ('written_content', 'Written Works'),
    ]

    for table, label in tables:
        try:
            count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[label] = count
        except:
            stats[label] = 0

    return stats


def get_world_info():
    """Get world name and altname."""
    db = get_db()
    if not db:
        return None

    try:
        row = db.execute("SELECT name, altname FROM world LIMIT 1").fetchone()
        if row:
            return {'name': row['name'], 'altname': row['altname']}
    except:
        pass
    return None


def get_current_year():
    """Get the current year of the world."""
    db = get_db()
    if not db:
        return None
    try:
        row = db.execute("SELECT MAX(MAX(birth_year), MAX(death_year)) as year FROM historical_figures WHERE death_year != -1").fetchone()
        return row['year'] if row else None
    except:
        return None


@app.route('/')
def index():
    """Dashboard page."""
    current_world = get_current_world()
    all_worlds = get_all_worlds()
    world = get_world_info()
    stats = get_stats()

    return render_template('index.html',
                         world=world,
                         stats=stats,
                         current_world=current_world,
                         all_worlds=all_worlds)


@app.route('/switch-world/<world_id>', methods=['POST'])
def switch_world(world_id):
    """Switch to a different world."""
    db = get_master_db()
    cursor = db.cursor()

    # Verify world exists
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('index'))

    # Switch current world
    cursor.execute("UPDATE worlds SET is_current = 0 WHERE is_current = 1")
    cursor.execute("UPDATE worlds SET is_current = 1 WHERE id = ?", (world_id,))
    db.commit()

    flash(f"Switched to world: {world['name']}", 'success')
    return redirect(url_for('index'))


@app.route('/delete-world/<world_id>', methods=['POST'])
def delete_world(world_id):
    """Delete a world and its database."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('index'))

    # Delete database file and WAL journal files
    db_path = Path(world['db_path'])
    if db_path.exists():
        db_path.unlink()
    # Clean up WAL journal files
    wal_path = db_path.with_suffix('.db-wal')
    shm_path = db_path.with_suffix('.db-shm')
    if wal_path.exists():
        wal_path.unlink()
    if shm_path.exists():
        shm_path.unlink()
    # Clean up map file if exists
    map_path = db_path.with_name(f'{world_id}_map.png')
    if map_path.exists():
        map_path.unlink()

    # Remove from master database
    cursor.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
    db.commit()

    flash(f"Deleted world: {world['name']}", 'success')
    return redirect(url_for('index'))


def save_world_map(world_id, map_file):
    """Save world map image, converting BMP to PNG if needed."""
    try:
        # Read image
        img = Image.open(map_file)

        # Save as PNG in worlds directory
        map_path = DATA_DIR / 'worlds' / f'{world_id}_map.png'
        img.save(map_path, 'PNG')

        # Update has_map flag
        db = get_master_db()
        db.execute("UPDATE worlds SET has_map = 1 WHERE id = ?", (world_id,))
        db.commit()

        return True
    except Exception as e:
        print(f"Error saving map: {e}")
        return False


@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and run import."""
    # Check for legends file (required)
    if 'legends' not in request.files or request.files['legends'].filename == '':
        flash('legends.xml file is required', 'error')
        return redirect(url_for('index'))

    legends_file = request.files['legends']
    plus_file = request.files.get('legends_plus')
    map_file = request.files.get('world_map')

    # Create uploads directory
    upload_dir = DATA_DIR / 'uploads'
    upload_dir.mkdir(exist_ok=True)

    # Save uploaded files
    legends_path = upload_dir / 'legends.xml'
    legends_file.save(legends_path)

    plus_path = None
    if plus_file and plus_file.filename:
        plus_path = upload_dir / 'legends_plus.xml'
        plus_file.save(plus_path)

    # Run import with file paths
    try:
        cmd = [sys.executable, str(BASE_DIR / 'build.py'), str(legends_path)]
        if plus_path:
            cmd.append(str(plus_path))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            flash('Import completed successfully!', 'success')

            # If map file provided, save it for the newly created world
            if map_file and map_file.filename:
                # Get the world that was just created (most recent)
                world = get_current_world()
                if world:
                    if save_world_map(world['id'], map_file):
                        flash('World map uploaded!', 'success')
                    else:
                        flash('Failed to save world map', 'error')
        else:
            flash(f'Import failed: {result.stderr}', 'error')

        # Store output for display
        app.config['LAST_BUILD_OUTPUT'] = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        flash('Import timed out after 10 minutes', 'error')
    except Exception as e:
        flash(f'Error running import: {str(e)}', 'error')
    finally:
        # Cleanup uploaded files
        if legends_path.exists():
            legends_path.unlink()
        if plus_path and plus_path.exists():
            plus_path.unlink()

    return redirect(url_for('index'))


@app.route('/merge-plus/<world_id>', methods=['POST'])
def merge_plus(world_id):
    """Merge legends_plus.xml into an existing world."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('index'))

    if world['has_plus']:
        flash('This world already has legends_plus data', 'error')
        return redirect(url_for('index'))

    # Check for legends_plus file
    if 'legends_plus' not in request.files or request.files['legends_plus'].filename == '':
        flash('legends_plus.xml file is required', 'error')
        return redirect(url_for('index'))

    plus_file = request.files['legends_plus']

    # Create uploads directory
    upload_dir = DATA_DIR / 'uploads'
    upload_dir.mkdir(exist_ok=True)

    # Save uploaded file
    plus_path = upload_dir / 'legends_plus.xml'
    plus_file.save(plus_path)

    # Run merge with file path
    try:
        cmd = [
            sys.executable, str(BASE_DIR / 'build.py'),
            '--merge', world_id, world['db_path'], str(plus_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            flash('Legends+ data merged successfully!', 'success')
        else:
            flash(f'Merge failed: {result.stderr}', 'error')

        # Store output for display
        app.config['LAST_BUILD_OUTPUT'] = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        flash('Merge timed out after 10 minutes', 'error')
    except Exception as e:
        flash(f'Error running merge: {str(e)}', 'error')
    finally:
        # Cleanup uploaded file
        if plus_path.exists():
            plus_path.unlink()

    return redirect(url_for('index'))


@app.route('/upload-map/<world_id>', methods=['POST'])
def upload_map(world_id):
    """Upload world map image for an existing world."""
    db = get_master_db()
    cursor = db.cursor()

    # Get world info
    world = cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,)).fetchone()
    if not world:
        flash('World not found', 'error')
        return redirect(url_for('index'))

    # Check for map file
    if 'world_map' not in request.files or request.files['world_map'].filename == '':
        flash('Map file is required', 'error')
        return redirect(url_for('index'))

    map_file = request.files['world_map']

    if save_world_map(world_id, map_file):
        flash('World map uploaded successfully!', 'success')
    else:
        flash('Failed to save world map', 'error')

    return redirect(url_for('index'))


@app.route('/world-map-image/<world_id>')
def world_map_image(world_id):
    """Serve the world map image (terrain or uploaded)."""
    # Prefer generated terrain map
    terrain_path = DATA_DIR / 'worlds' / f'{world_id}_terrain.png'
    if terrain_path.exists():
        return send_file(terrain_path, mimetype='image/png')
    # Fall back to uploaded map
    map_path = DATA_DIR / 'worlds' / f'{world_id}_map.png'
    if map_path.exists():
        return send_file(map_path, mimetype='image/png')
    else:
        return '', 404


@app.route('/build-output')
def build_output():
    """Show last build output."""
    output = app.config.get('LAST_BUILD_OUTPUT', 'No build output available.')
    return render_template('output.html', output=output)


@app.route('/figures')
def figures():
    """List historical figures."""
    db = get_db()
    if not db:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Database not found'})
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    search = request.args.get('q', '')
    race_filter = request.args.get('race', '')
    alive_filter = request.args.get('alive', '') == '1'

    # Sorting
    sort_col = request.args.get('sort', 'name')
    sort_dir = request.args.get('dir', 'asc')

    # Validate sort column and direction
    valid_columns = ['id', 'name', 'race', 'caste', 'birth_year', 'death_year']
    if sort_col not in valid_columns:
        sort_col = 'name'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    query = """SELECT hf.*,
               (SELECT COUNT(*) FROM hf_entity_links WHERE hfid = hf.id) +
               (SELECT COUNT(*) FROM hf_site_links WHERE hfid = hf.id) as link_count
               FROM historical_figures hf WHERE 1=1"""
    count_query = "SELECT COUNT(*) FROM historical_figures WHERE 1=1"
    params = []
    count_params = []

    if search:
        query += " AND name LIKE ?"
        count_query += " AND name LIKE ?"
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')

    if race_filter:
        query += " AND race = ?"
        count_query += " AND race = ?"
        params.append(race_filter)
        count_params.append(race_filter)

    if alive_filter:
        query += " AND death_year = -1"
        count_query += " AND death_year = -1"

    # Handle NULL sorting (NULLs last for ASC, first for DESC)
    if sort_dir == 'asc':
        query += f" ORDER BY hf.{sort_col} IS NULL, hf.{sort_col} ASC"
    else:
        query += f" ORDER BY hf.{sort_col} IS NOT NULL, hf.{sort_col} DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    figures_data = db.execute(query, params).fetchall()
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page  # Ceiling division

    current_year = get_current_year()

    # AJAX request - return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        figures_list = []
        for row in figures_data:
            fig = dict(row)
            race_info = get_race_info(fig.get('race'), fig.get('caste'))
            fig['race_label'] = race_info['label']
            fig['race_icon'] = race_info['icon']
            fig['race_img'] = race_info['img']
            # Calculate age
            if fig.get('birth_year') is not None and current_year is not None:
                if fig.get('death_year') == -1:  # Still alive
                    fig['age'] = current_year - fig['birth_year']
                elif fig.get('death_year') is not None:
                    fig['age'] = fig['death_year'] - fig['birth_year']
                else:
                    fig['age'] = None
            else:
                fig['age'] = None
            figures_list.append(fig)
        return jsonify({
            'figures': figures_list,
            'total': total,
            'total_pages': total_pages,
            'page': page,
            'per_page': per_page,
            'current_year': current_year,
            'sort': sort_col,
            'dir': sort_dir
        })

    # Get unique races for filter
    races = db.execute("SELECT DISTINCT race FROM historical_figures WHERE race IS NOT NULL ORDER BY race").fetchall()

    # Check if DFHack data is available
    current_world = get_current_world()
    has_plus = current_world and current_world.get('has_plus')

    return render_template('figures.html',
                         figures=figures_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         search=search,
                         race_filter=race_filter,
                         alive_filter=alive_filter,
                         races=races,
                         current_year=current_year,
                         sort=sort_col,
                         dir=sort_dir,
                         has_plus=has_plus)


@app.route('/figures/<int:figure_id>/affiliations')
def figure_affiliations(figure_id):
    """Get entity affiliations and site links for a specific historical figure."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    # Entity affiliations
    affiliations = db.execute("""
        SELECT hel.*, e.name as entity_name, e.type as entity_type
        FROM hf_entity_links hel
        LEFT JOIN entities e ON hel.entity_id = e.id
        WHERE hel.hfid = ?
        ORDER BY hel.link_type, e.name
    """, [figure_id]).fetchall()

    affiliations_list = []
    for row in affiliations:
        aff = dict(row)
        affiliations_list.append(aff)

    # Site links
    site_links = db.execute("""
        SELECT hsl.*, s.name as site_name, s.type as site_type
        FROM hf_site_links hsl
        LEFT JOIN sites s ON hsl.site_id = s.id
        WHERE hsl.hfid = ?
        ORDER BY hsl.link_type, s.name
    """, [figure_id]).fetchall()

    site_links_list = []
    for row in site_links:
        sl = dict(row)
        site_type_info = get_site_type_info(sl.get('site_type'))
        sl['site_type_label'] = site_type_info['label']
        sl['site_type_icon'] = site_type_info['icon']
        sl['site_type_img'] = site_type_info['img']
        site_links_list.append(sl)

    return jsonify({
        'affiliations': affiliations_list,
        'site_links': site_links_list
    })


@app.route('/sites')
def sites():
    """List sites."""
    db = get_db()
    if not db:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Database not found'})
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    search = request.args.get('q', '')
    type_filter = request.args.get('type', '')

    # Sorting
    sort_col = request.args.get('sort', 'name')
    sort_dir = request.args.get('dir', 'asc')

    # Validate sort column and direction
    valid_columns = ['id', 'name', 'type', 'settlers']
    if sort_col not in valid_columns:
        sort_col = 'name'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    query = """SELECT s.*, e.race as civ_race,
               (SELECT COUNT(*) FROM structures st WHERE st.site_id = s.id) as structure_count,
               (SELECT COUNT(*) FROM hf_site_links hsl
                JOIN historical_figures hf ON hsl.hfid = hf.id
                WHERE hsl.site_id = s.id AND hf.death_year = -1) as settlers
               FROM sites s
               LEFT JOIN entities e ON s.civ_id = e.id
               WHERE 1=1"""
    count_query = "SELECT COUNT(*) FROM sites WHERE 1=1"
    params = []
    count_params = []

    if search:
        # Search in site name OR structure names
        query += """ AND (s.name LIKE ? OR s.id IN (
            SELECT DISTINCT site_id FROM structures WHERE name LIKE ?
        ))"""
        count_query += """ AND (name LIKE ? OR id IN (
            SELECT DISTINCT site_id FROM structures WHERE name LIKE ?
        ))"""
        params.extend([f'%{search}%', f'%{search}%'])
        count_params.extend([f'%{search}%', f'%{search}%'])

    if type_filter:
        query += " AND s.type = ?"
        count_query += " AND type = ?"
        params.append(type_filter)
        count_params.append(type_filter)

    # Handle NULL sorting (NULLs last for ASC, first for DESC)
    sort_prefix = "s." if sort_col in ['id', 'name', 'type', 'coords'] else ""
    if sort_dir == 'asc':
        query += f" ORDER BY {sort_prefix}{sort_col} IS NULL, {sort_prefix}{sort_col} ASC"
    else:
        query += f" ORDER BY {sort_prefix}{sort_col} IS NOT NULL, {sort_prefix}{sort_col} DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    sites_data = db.execute(query, params).fetchall()
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # AJAX request - return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        sites_list = []
        for row in sites_data:
            site = dict(row)
            type_info = get_site_type_info(site.get('type'))
            site['type_label'] = type_info['label']
            site['type_icon'] = type_info['icon']
            site['type_img'] = type_info['img']
            # Add civ race info
            civ_race = site.get('civ_race')
            if civ_race:
                race_info = get_race_info(civ_race.upper())
                site['civ_label'] = race_info['label']
                site['civ_icon'] = race_info['icon']
                site['civ_img'] = race_info['img']
            else:
                site['civ_label'] = None
                site['civ_icon'] = None
                site['civ_img'] = None
            sites_list.append(site)
        return jsonify({
            'sites': sites_list,
            'total': total,
            'total_pages': total_pages,
            'page': page,
            'per_page': per_page,
            'sort': sort_col,
            'dir': sort_dir
        })

    # Get unique types for filter
    types = db.execute("SELECT DISTINCT type FROM sites WHERE type IS NOT NULL ORDER BY type").fetchall()

    current_world = get_current_world()
    has_plus = current_world and current_world.get('has_plus')

    return render_template('sites.html',
                         sites=sites_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         search=search,
                         type_filter=type_filter,
                         types=types,
                         sort=sort_col,
                         dir=sort_dir,
                         has_plus=has_plus)


@app.route('/sites/<int:site_id>/structures')
def site_structures(site_id):
    """Get structures for a specific site."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    search = request.args.get('q', '')

    structures = db.execute(
        "SELECT * FROM structures WHERE site_id = ? ORDER BY type, name",
        [site_id]
    ).fetchall()

    structures_list = []
    for row in structures:
        struct = dict(row)
        type_info = get_structure_type_info(struct.get('type'))
        struct['type_label'] = type_info['label']
        struct['type_icon'] = type_info['icon']
        struct['type_img'] = type_info['img']
        # Mark if this structure matches the search
        if search:
            struct['matches'] = search.lower() in (struct.get('name') or '').lower()
        structures_list.append(struct)

    return jsonify({'structures': structures_list})


@app.route('/map')
def world_map():
    """Display world map with sites."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    current_world = get_current_world()

    # Get world bounds from regions (same as terrain map generator)
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0
    regions_data = db.execute("""
        SELECT coords FROM regions WHERE coords IS NOT NULL AND coords != ''
    """).fetchall()

    for (coords_str,) in regions_data:
        for pair in coords_str.split('|'):
            if ',' in pair:
                try:
                    x, y = map(int, pair.split(','))
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
                except ValueError:
                    continue

    # Fallback if no regions
    if min_x == float('inf'):
        min_x, min_y, max_x, max_y = 0, 0, 128, 128

    # Calculate map dimensions from regions
    map_width = max_x - min_x + 1
    map_height = max_y - min_y + 1

    # Get all sites with coordinates
    sites_data = db.execute("""
        SELECT s.id, s.name, s.type, s.coords, e.race as civ_race
        FROM sites s
        LEFT JOIN entities e ON s.civ_id = e.id
        WHERE s.coords IS NOT NULL AND s.coords != ''
    """).fetchall()

    # Parse site coordinates
    sites_list = []
    for row in sites_data:
        site = dict(row)
        try:
            x, y = map(int, site['coords'].split(','))
            site['x'] = x
            site['y'] = y

            type_info = get_site_type_info(site.get('type'))
            site['type_label'] = type_info['label']
            site['type_icon'] = type_info['icon']
            site['type_img'] = type_info['img']

            if site.get('civ_race'):
                race_info = get_race_info(site['civ_race'].upper())
                site['civ_label'] = race_info['label']
            else:
                site['civ_label'] = None

            sites_list.append(site)
        except (ValueError, AttributeError):
            continue

    # Get site type counts for legend
    type_counts = db.execute("""
        SELECT type, COUNT(*) as count FROM sites
        WHERE coords IS NOT NULL AND coords != ''
        GROUP BY type ORDER BY count DESC
    """).fetchall()

    # Get mountain peaks with coordinates
    peaks_data = db.execute("""
        SELECT id, name, coords, height, is_volcano
        FROM mountain_peaks
        WHERE coords IS NOT NULL AND coords != ''
    """).fetchall()

    peaks_list = []
    for row in peaks_data:
        peak = dict(row)
        try:
            x, y = map(int, peak['coords'].split(','))
            peak['x'] = x
            peak['y'] = y
            peaks_list.append(peak)
        except (ValueError, AttributeError):
            continue

    # Check if map image exists (terrain or uploaded)
    world_id = current_world['id'] if current_world else None
    has_map = False
    if world_id:
        terrain_path = DATA_DIR / 'worlds' / f'{world_id}_terrain.png'
        map_path = DATA_DIR / 'worlds' / f'{world_id}_map.png'
        has_map = terrain_path.exists() or map_path.exists()

    return render_template('map.html',
                         sites=sites_list,
                         peaks=peaks_list,
                         min_x=min_x,
                         min_y=min_y,
                         map_width=map_width,
                         map_height=map_height,
                         type_counts=type_counts,
                         total_sites=len(sites_list),
                         total_peaks=len(peaks_list),
                         has_map=has_map,
                         world_id=world_id,
                         world=current_world)


@app.route('/map/search')
def map_search():
    """Search sites for map navigation."""
    db = get_db()
    if not db:
        return jsonify([])

    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])

    # Search sites by name, limit to 5 results
    sites_data = db.execute("""
        SELECT id, name, type, coords
        FROM sites
        WHERE coords IS NOT NULL AND coords != ''
        AND name LIKE ?
        ORDER BY name
        LIMIT 5
    """, [f'%{q}%']).fetchall()

    results = []
    for row in sites_data:
        site = dict(row)
        type_info = get_site_type_info(site.get('type'))
        try:
            x, y = map(int, site['coords'].split(','))
            results.append({
                'id': site['id'],
                'name': site['name'] or '(unnamed)',
                'type': type_info['label'],
                'type_icon': type_info['icon'],
                'type_img': type_info['img'],
                'x': x,
                'y': y
            })
        except (ValueError, AttributeError):
            continue

    return jsonify(results)


@app.route('/peak/<int:peak_id>')
def peak_detail(peak_id):
    """Display mountain peak details."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    peak = db.execute(
        "SELECT * FROM mountain_peaks WHERE id = ?",
        [peak_id]
    ).fetchone()

    if not peak:
        flash('Peak not found.', 'error')
        return redirect(url_for('world_map'))

    peak = dict(peak)

    # Parse coordinates
    if peak.get('coords'):
        try:
            x, y = map(int, peak['coords'].split(','))
            peak['x'] = x
            peak['y'] = y
        except (ValueError, AttributeError):
            pass

    return render_template('peak.html', peak=peak)


@app.route('/events')
def events():
    """List historical events."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    year_filter = request.args.get('year', '', type=str)
    type_filter = request.args.get('type', '')

    query = "SELECT * FROM historical_events WHERE 1=1"
    params = []

    if year_filter:
        query += " AND year = ?"
        params.append(year_filter)

    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)

    query += " ORDER BY year DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    events_data = db.execute(query, params).fetchall()
    count_query = "SELECT COUNT(*) FROM historical_events WHERE 1=1"
    count_params = []
    if year_filter:
        count_query += " AND year = ?"
        count_params.append(year_filter)
    if type_filter:
        count_query += " AND type = ?"
        count_params.append(type_filter)
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # Get unique types for filter
    types = db.execute("SELECT DISTINCT type FROM historical_events WHERE type IS NOT NULL ORDER BY type").fetchall()

    return render_template('events.html',
                         events=events_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         year_filter=year_filter,
                         type_filter=type_filter,
                         types=types)


@app.route('/artifacts')
def artifacts():
    """List artifacts."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    search = request.args.get('q', '')
    type_filter = request.args.get('type', '')

    # Sorting
    sort_col = request.args.get('sort', 'name')
    sort_dir = request.args.get('dir', 'asc')

    valid_columns = ['id', 'name', 'item_type', 'mat']
    if sort_col not in valid_columns:
        sort_col = 'name'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    query = """SELECT a.*,
               hf.name as creator_name,
               hf.race as creator_race,
               s.name as site_name,
               s.type as site_type,
               holder.name as holder_name,
               holder.race as holder_race
               FROM artifacts a
               LEFT JOIN historical_figures hf ON a.creator_hfid = hf.id
               LEFT JOIN sites s ON a.site_id = s.id
               LEFT JOIN historical_figures holder ON a.holder_hfid = holder.id
               WHERE a.name IS NOT NULL"""
    count_query = "SELECT COUNT(*) FROM artifacts WHERE name IS NOT NULL"
    params = []
    count_params = []

    if search:
        query += " AND a.name LIKE ?"
        count_query += " AND name LIKE ?"
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')

    if type_filter:
        query += " AND a.item_type = ?"
        count_query += " AND item_type = ?"
        params.append(type_filter)
        count_params.append(type_filter)

    # Handle NULL sorting
    if sort_dir == 'asc':
        query += f" ORDER BY a.{sort_col} IS NULL, a.{sort_col} ASC"
    else:
        query += f" ORDER BY a.{sort_col} IS NOT NULL, a.{sort_col} DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    artifacts_data = db.execute(query, params).fetchall()
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # Get unique types for filter
    types = db.execute("SELECT DISTINCT item_type FROM artifacts WHERE item_type IS NOT NULL ORDER BY item_type").fetchall()

    current_world = get_current_world()
    has_plus = current_world and current_world.get('has_plus')

    return render_template('artifacts.html',
                         artifacts=artifacts_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         search=search,
                         type_filter=type_filter,
                         types=types,
                         sort=sort_col,
                         dir=sort_dir,
                         has_plus=has_plus)


@app.route('/written')
def written_content():
    """List written content."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    search = request.args.get('q', '')
    type_filter = request.args.get('type', '')

    # Sorting
    sort_col = request.args.get('sort', 'title')
    sort_dir = request.args.get('dir', 'asc')

    valid_columns = ['id', 'title', 'type']
    if sort_col not in valid_columns:
        sort_col = 'title'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    query = """SELECT wc.*,
               hf.name as author_name,
               hf.race as author_race,
               a.id as artifact_id,
               a.item_type as artifact_type,
               a.item_subtype as artifact_subtype
               FROM written_content wc
               LEFT JOIN historical_figures hf ON wc.author_hfid = hf.id
               LEFT JOIN artifacts a ON a.name = wc.title COLLATE NOCASE
               WHERE 1=1"""
    count_query = "SELECT COUNT(*) FROM written_content WHERE 1=1"
    params = []
    count_params = []

    if search:
        query += " AND wc.title LIKE ?"
        count_query += " AND title LIKE ?"
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')

    if type_filter:
        query += " AND wc.type = ?"
        count_query += " AND type = ?"
        params.append(type_filter)
        count_params.append(type_filter)

    # Handle NULL sorting
    if sort_dir == 'asc':
        query += f" ORDER BY wc.{sort_col} IS NULL, wc.{sort_col} ASC"
    else:
        query += f" ORDER BY wc.{sort_col} IS NOT NULL, wc.{sort_col} DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    written_data = db.execute(query, params).fetchall()
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # Get unique types for filter
    types = db.execute("SELECT DISTINCT type FROM written_content WHERE type IS NOT NULL ORDER BY type").fetchall()

    current_world = get_current_world()
    has_plus = current_world and current_world.get('has_plus')

    return render_template('written.html',
                         written=written_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         search=search,
                         type_filter=type_filter,
                         types=types,
                         sort=sort_col,
                         dir=sort_dir,
                         has_plus=has_plus)


# ==================== API Endpoints for Modal ====================

@app.route('/api/figure/<int:figure_id>')
def api_figure(figure_id):
    """Get figure details for modal."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    figure = db.execute("""
        SELECT * FROM historical_figures WHERE id = ?
    """, [figure_id]).fetchone()

    if not figure:
        return jsonify({'error': 'Figure not found'}), 404

    fig = dict(figure)
    race_info = get_race_info(fig.get('race'), fig.get('caste'))
    fig['race_label'] = race_info['label']
    fig['race_img'] = race_info['img']

    # Calculate age
    current_year = get_current_year()
    if fig.get('birth_year') is not None and current_year is not None:
        if fig.get('death_year') == -1:
            fig['age'] = current_year - fig['birth_year']
        elif fig.get('death_year') is not None:
            fig['age'] = fig['death_year'] - fig['birth_year']

    # Get affiliations
    affiliations = db.execute("""
        SELECT hel.*, e.name as entity_name, e.type as entity_type, e.race as entity_race
        FROM hf_entity_links hel
        LEFT JOIN entities e ON hel.entity_id = e.id
        WHERE hel.hfid = ?
        ORDER BY hel.link_type, e.name
    """, [figure_id]).fetchall()

    # Get site links
    site_links = db.execute("""
        SELECT hsl.*, s.name as site_name, s.type as site_type
        FROM hf_site_links hsl
        LEFT JOIN sites s ON hsl.site_id = s.id
        WHERE hsl.hfid = ?
        ORDER BY hsl.link_type, s.name
    """, [figure_id]).fetchall()

    # Get relationships (where this figure is source or target)
    relationships_raw = db.execute("""
        SELECT r.*,
               hf.name as related_name, hf.race as related_race, hf.caste as related_caste
        FROM hf_relationships r
        LEFT JOIN historical_figures hf ON (
            CASE WHEN r.source_hf = ? THEN r.target_hf ELSE r.source_hf END
        ) = hf.id
        WHERE r.source_hf = ? OR r.target_hf = ?
        ORDER BY r.relationship, r.year
    """, [figure_id, figure_id, figure_id]).fetchall()

    relationships = []
    for rel in relationships_raw:
        r = dict(rel)
        if r.get('related_race'):
            race_info = get_race_info(r['related_race'], r.get('related_caste'))
            r['related_race_img'] = race_info['img']
        relationships.append(r)

    # Get life events (where this figure is involved)
    # hfid is direct column, other figure refs may be in extra_data JSON
    # victim_hf is used for hist_figure_died events (victim stored in extra_data)
    events = db.execute("""
        SELECT e.*, s.name as site_name, s.type as site_type,
               slayer.name as slayer_name, slayer.race as slayer_race
        FROM historical_events e
        LEFT JOIN sites s ON e.site_id = s.id
        LEFT JOIN historical_figures slayer ON e.slayer_hfid = slayer.id
        WHERE e.hfid = ? OR e.slayer_hfid = ?
           OR e.extra_data LIKE ?
           OR e.extra_data LIKE ?
        ORDER BY e.year ASC, e.id ASC
        LIMIT 100
    """, [figure_id, figure_id, f'%"hfid2": "{figure_id}"%', f'%"victim_hf": "{figure_id}"%']).fetchall()

    events_list = []
    for ev in events:
        ev_dict = dict(ev)
        ev_dict['type_label'] = get_event_type_info(ev_dict.get('type'))['label']
        # Parse extra_data to get hfid2 name and victim_hf name if present
        if ev_dict.get('extra_data'):
            try:
                import json
                extra = json.loads(ev_dict['extra_data'])
                hfid2 = extra.get('hfid2') or extra.get('hf_target')
                if hfid2:
                    hf2 = db.execute("SELECT name FROM historical_figures WHERE id = ?", [hfid2]).fetchone()
                    if hf2:
                        ev_dict['hfid2'] = hfid2
                        ev_dict['hfid2_name'] = hf2['name']
                # Get victim name and race for death events
                victim_hf = extra.get('victim_hf')
                if victim_hf:
                    victim = db.execute("SELECT name, race FROM historical_figures WHERE id = ?", [victim_hf]).fetchone()
                    if victim:
                        ev_dict['victim_hfid'] = victim_hf
                        ev_dict['victim_name'] = victim['name']
                        ev_dict['victim_race'] = victim['race']
            except:
                pass
        # Get artifact name/type for artifact_created events
        artifact_id = ev_dict.get('artifact_id')
        if artifact_id:
            artifact = db.execute("SELECT name, item_type FROM artifacts WHERE id = ?", [artifact_id]).fetchone()
            if artifact:
                ev_dict['artifact_name'] = artifact['name']
                ev_dict['artifact_type'] = artifact['item_type']
        events_list.append(ev_dict)

    return jsonify({
        'figure': fig,
        'affiliations': [dict(a) for a in affiliations],
        'site_links': [dict(s) for s in site_links],
        'relationships': relationships,
        'events': events_list
    })


@app.route('/api/site/<int:site_id>')
def api_site(site_id):
    """Get site details for modal."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    # Get site with civilization and current owner info
    site = db.execute("""
        SELECT s.*,
               e.name as civ_name, e.race as civ_race,
               owner.name as owner_name, owner.race as owner_race
        FROM sites s
        LEFT JOIN entities e ON s.civ_id = e.id
        LEFT JOIN entities owner ON s.cur_owner_id = owner.id
        WHERE s.id = ?
    """, [site_id]).fetchone()

    if not site:
        return jsonify({'error': 'Site not found'}), 404

    site_dict = dict(site)
    type_info = get_site_type_info(site_dict.get('type'))
    site_dict['type_label'] = type_info['label']

    # Get structures
    structures = db.execute("""
        SELECT * FROM structures WHERE site_id = ? ORDER BY type, name
    """, [site_id]).fetchall()

    structures_list = []
    for s in structures:
        st = dict(s)
        st_info = get_structure_type_info(st.get('type'))
        st['type_label'] = st_info['label']
        structures_list.append(st)

    # Get linked historical figures
    linked_figures = db.execute("""
        SELECT hf.id, hf.name, hf.race, hf.caste, hsl.link_type
        FROM hf_site_links hsl
        JOIN historical_figures hf ON hsl.hfid = hf.id
        WHERE hsl.site_id = ?
        ORDER BY hsl.link_type, hf.name
        LIMIT 50
    """, [site_id]).fetchall()

    figures_list = []
    for row in linked_figures:
        f = dict(row)
        race = f.get('race') or ''
        race_info = get_race_info(race.upper(), f.get('caste'))
        f['race_icon'] = race_info['icon']
        f['race_img'] = race_info['img']
        f['race_label'] = race_info['label']
        figures_list.append(f)

    # Get current settlers (alive figures linked to this site)
    settlers = db.execute("""
        SELECT hf.id, hf.name, hf.race, hf.caste, hsl.link_type
        FROM hf_site_links hsl
        JOIN historical_figures hf ON hsl.hfid = hf.id
        WHERE hsl.site_id = ? AND hf.death_year = -1
        ORDER BY hf.race, hf.name
        LIMIT 100
    """, [site_id]).fetchall()

    settlers_list = []
    for row in settlers:
        s = dict(row)
        race = s.get('race') or ''
        race_info = get_race_info(race.upper(), s.get('caste'))
        s['race_icon'] = race_info['icon']
        s['race_img'] = race_info['img']
        s['race_label'] = race_info['label']
        settlers_list.append(s)

    # Get artifacts at this site
    artifacts = db.execute("""
        SELECT id, name, item_type, item_subtype
        FROM artifacts
        WHERE site_id = ?
        ORDER BY name
        LIMIT 20
    """, [site_id]).fetchall()

    artifacts_list = [dict(a) for a in artifacts]

    # Get historical events at this site (limited)
    events_cursor = db.execute("""
        SELECT he.id, he.year, he.type, he.hfid, he.slayer_hfid, he.extra_data,
               he.state, he.reason, he.death_cause, he.artifact_id, he.civ_id, he.entity_id,
               hf.name as hf_name, hf.race as hf_race,
               slayer.name as slayer_name, slayer.race as slayer_race
        FROM historical_events he
        LEFT JOIN historical_figures hf ON he.hfid = hf.id
        LEFT JOIN historical_figures slayer ON he.slayer_hfid = slayer.id
        WHERE he.site_id = ?
        ORDER BY he.year DESC
        LIMIT 20
    """, [site_id])

    events_list = []
    for ev_row in events_cursor.fetchall():
        ev = {
            'id': ev_row['id'],
            'year': ev_row['year'],
            'type': ev_row['type'],
            'hfid': ev_row['hfid'],
            'slayer_hfid': ev_row['slayer_hfid'],
            'hf_name': ev_row['hf_name'],
            'hf_race': ev_row['hf_race'],
            'slayer_name': ev_row['slayer_name'],
            'slayer_race': ev_row['slayer_race'],
            'state': ev_row['state'],
            'reason': ev_row['reason'],
            'death_cause': ev_row['death_cause'],
            'artifact_id': ev_row['artifact_id'],
            'civ_id': ev_row['civ_id'],
            'entity_id': ev_row['entity_id'],
            'extra_data': ev_row['extra_data']
        }
        # Get artifact name/type for artifact events
        if ev['artifact_id']:
            artifact = db.execute("SELECT name, item_type FROM artifacts WHERE id = ?", [ev['artifact_id']]).fetchone()
            if artifact:
                ev['artifact_name'] = artifact['name']
                ev['artifact_type'] = artifact['item_type']
        events_list.append(ev)

    return jsonify({
        'site': site_dict,
        'structures': structures_list,
        'linked_figures': figures_list,
        'settlers': settlers_list,
        'artifacts': artifacts_list,
        'events': events_list
    })


@app.route('/api/artifact/<int:artifact_id>')
def api_artifact(artifact_id):
    """Get artifact details for modal."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    artifact = db.execute("""
        SELECT a.*,
               hf.name as creator_name,
               s.name as site_name, s.type as site_type,
               holder.name as holder_name
        FROM artifacts a
        LEFT JOIN historical_figures hf ON a.creator_hfid = hf.id
        LEFT JOIN sites s ON a.site_id = s.id
        LEFT JOIN historical_figures holder ON a.holder_hfid = holder.id
        WHERE a.id = ?
    """, [artifact_id]).fetchone()

    if not artifact:
        return jsonify({'error': 'Artifact not found'}), 404

    art_dict = dict(artifact)

    # Get written content contained in this artifact (for books/scrolls)
    written_contents = db.execute("""
        SELECT wc.id, wc.title, wc.type
        FROM written_content wc
        WHERE wc.title = ? COLLATE NOCASE
        ORDER BY wc.page_start
    """, [art_dict.get('name')]).fetchall()

    written_list = [dict(wc) for wc in written_contents]

    return jsonify({
        'artifact': art_dict,
        'written_contents': written_list
    })


@app.route('/api/entity/<int:entity_id>')
def api_entity(entity_id):
    """Get entity details for modal."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    entity = db.execute("""
        SELECT * FROM entities WHERE id = ?
    """, [entity_id]).fetchone()

    if not entity:
        return jsonify({'error': 'Entity not found'}), 404

    ent = dict(entity)
    if ent.get('race'):
        race_info = get_race_info(ent['race'].upper())
        ent['race_label'] = race_info['label']

    # Get positions with current holders
    positions = db.execute("""
        SELECT ep.*, epa.histfig_id, hf.name as holder_name, hf.race as holder_race, hf.caste as holder_caste
        FROM entity_positions ep
        LEFT JOIN entity_position_assignments epa ON ep.entity_id = epa.entity_id AND ep.position_id = epa.position_id
        LEFT JOIN historical_figures hf ON epa.histfig_id = hf.id
        WHERE ep.entity_id = ?
        ORDER BY ep.name
    """, [entity_id]).fetchall()

    positions_list = []
    for p in positions:
        pos = dict(p)
        if pos.get('holder_race'):
            holder_race_info = get_race_info(pos['holder_race'].upper(), pos.get('holder_caste'))
            pos['holder_race_img'] = holder_race_info['img']
        positions_list.append(pos)

    return jsonify({
        'entity': ent,
        'positions': positions_list
    })


@app.route('/api/written/<int:written_id>')
def api_written(written_id):
    """Get written content details for modal."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    written = db.execute("""
        SELECT wc.*,
               hf.name as author_name, hf.race as author_race, hf.caste as author_caste
        FROM written_content wc
        LEFT JOIN historical_figures hf ON wc.author_hfid = hf.id
        WHERE wc.id = ?
    """, [written_id]).fetchone()

    if not written:
        return jsonify({'error': 'Written content not found'}), 404

    wc = dict(written)

    # Get author race info
    if wc.get('author_race'):
        author_race_info = get_race_info(wc['author_race'], wc.get('author_caste'))
        wc['author_race_label'] = author_race_info['label']
        wc['author_race_img'] = author_race_info['img']

    # Get written content type info
    type_info = get_written_type_info(wc.get('type'))
    wc['type_label'] = type_info['label']
    wc['type_img'] = type_info.get('img')
    wc['type_color'] = type_info.get('color')

    # Get styles
    styles = db.execute("""
        SELECT style FROM written_content_styles WHERE written_content_id = ?
    """, [written_id]).fetchall()
    wc['styles'] = [s['style'] for s in styles]

    # Get references - resolve them to actual entities
    references_raw = db.execute("""
        SELECT ref_type, ref_id FROM written_content_references WHERE written_content_id = ?
    """, [written_id]).fetchall()

    references = []
    for ref in references_raw:
        ref_data = {'type': ref['ref_type'], 'id': ref['ref_id']}

        if ref['ref_type'] == 'historical_figure':
            fig = db.execute("""
                SELECT id, name, race, caste FROM historical_figures WHERE id = ?
            """, [ref['ref_id']]).fetchone()
            if fig:
                ref_data['name'] = fig['name']
                ref_data['entity_type'] = 'figure'
                race_info = get_race_info(fig['race'], fig['caste'])
                ref_data['race_img'] = race_info['img']
        elif ref['ref_type'] == 'site':
            site = db.execute("""
                SELECT id, name, type FROM sites WHERE id = ?
            """, [ref['ref_id']]).fetchone()
            if site:
                ref_data['name'] = site['name']
                ref_data['entity_type'] = 'site'
                ref_data['site_type'] = site['type']
        elif ref['ref_type'] == 'entity':
            entity = db.execute("""
                SELECT id, name, type, race FROM entities WHERE id = ?
            """, [ref['ref_id']]).fetchone()
            if entity:
                ref_data['name'] = entity['name']
                ref_data['entity_type'] = 'entity'
                ref_data['entity_subtype'] = entity['type']
        elif ref['ref_type'] == 'artifact':
            artifact = db.execute("""
                SELECT id, name, item_type FROM artifacts WHERE id = ?
            """, [ref['ref_id']]).fetchone()
            if artifact:
                ref_data['name'] = artifact['name']
                ref_data['entity_type'] = 'artifact'
                ref_data['item_type'] = artifact['item_type']

        references.append(ref_data)

    # Find associated artifact (book/scroll containing this content)
    artifact = db.execute("""
        SELECT a.id, a.name, a.item_type, a.mat
        FROM artifacts a
        WHERE a.name = ? COLLATE NOCASE
    """, [wc.get('title')]).fetchone()

    artifact_data = None
    if artifact:
        artifact_data = dict(artifact)

    return jsonify({
        'written': wc,
        'references': references,
        'artifact': artifact_data
    })


if __name__ == '__main__':
    print("=" * 50)
    print("DF Tales Server")
    print("=" * 50)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Master database: {MASTER_DB_PATH}")
    print("\nStarting server at http://localhost:5001")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5001, host='0.0.0.0')
