#!/usr/bin/env python3
"""
DF-World Flask Application
Web interface for Dwarf Fortress legends data.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "world.db"

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


def get_race_info(race):
    """Get race label, text icon, and image icon path."""
    if not race:
        return {'label': '-', 'icon': '·', 'img': None}

    icon = '·'
    label = None
    img = None

    # Check for image icon (convention: static/icons/races/{RACE_CODE}.png or .gif)
    for ext in ['.png', '.gif']:
        icon_path = RACE_ICONS_DIR / f"{race}{ext}"
        if icon_path.exists():
            img = f'/static/icons/races/{race}{ext}'
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
app.secret_key = 'df-world-secret-key'

# Register template filters
app.jinja_env.filters['race_label'] = format_race
app.jinja_env.globals['get_race_info'] = get_race_info


def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        if DB_PATH.exists():
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
        else:
            g.db = None
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


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
    world = get_world_info()
    stats = get_stats()

    # Check for XML files
    xml_files = list(BASE_DIR.glob("*.xml"))
    has_xml = len(xml_files) >= 2

    return render_template('index.html',
                         world=world,
                         stats=stats,
                         has_xml=has_xml,
                         xml_files=[f.name for f in xml_files])


@app.route('/build', methods=['POST'])
def build():
    """Run the import script."""
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / 'build.py')],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            flash('Import completed successfully!', 'success')
        else:
            flash(f'Import failed: {result.stderr}', 'error')

        # Store output for display
        app.config['LAST_BUILD_OUTPUT'] = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        flash('Import timed out after 10 minutes', 'error')
    except Exception as e:
        flash(f'Error running import: {str(e)}', 'error')

    return redirect(url_for('index'))


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

    # Sorting
    sort_col = request.args.get('sort', 'name')
    sort_dir = request.args.get('dir', 'asc')

    # Validate sort column and direction
    valid_columns = ['id', 'name', 'race', 'caste', 'birth_year', 'death_year']
    if sort_col not in valid_columns:
        sort_col = 'name'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    query = "SELECT * FROM historical_figures WHERE 1=1"
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

    # Handle NULL sorting (NULLs last for ASC, first for DESC)
    if sort_dir == 'asc':
        query += f" ORDER BY {sort_col} IS NULL, {sort_col} ASC"
    else:
        query += f" ORDER BY {sort_col} IS NOT NULL, {sort_col} DESC"

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
            race_info = get_race_info(fig.get('race'))
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

    return render_template('figures.html',
                         figures=figures_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         search=search,
                         race_filter=race_filter,
                         races=races,
                         current_year=current_year,
                         sort=sort_col,
                         dir=sort_dir)


@app.route('/sites')
def sites():
    """List sites."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    type_filter = request.args.get('type', '')

    query = "SELECT * FROM sites WHERE 1=1"
    params = []

    if type_filter:
        query += " AND type = ?"
        params.append(type_filter)

    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    sites_data = db.execute(query, params).fetchall()
    count_query = "SELECT COUNT(*) FROM sites"
    count_params = []
    if type_filter:
        count_query += " WHERE type = ?"
        count_params.append(type_filter)
    total = db.execute(count_query, count_params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # Get unique types for filter
    types = db.execute("SELECT DISTINCT type FROM sites WHERE type IS NOT NULL ORDER BY type").fetchall()

    return render_template('sites.html',
                         sites=sites_data,
                         page=page,
                         total=total,
                         total_pages=total_pages,
                         per_page=per_page,
                         type_filter=type_filter,
                         types=types)


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


if __name__ == '__main__':
    print("=" * 50)
    print("DF-World Server")
    print("=" * 50)
    print(f"\nDatabase: {DB_PATH}")
    print(f"XML files should be in: {BASE_DIR}")
    print("\nStarting server at http://localhost:5001")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5001, host='0.0.0.0')
