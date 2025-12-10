"""
HTML page routes for DF Tales.
Handles figures, sites, map, events, artifacts, written content, and graph pages.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from db import get_db, get_current_world, get_current_year, DATA_DIR
from helpers import (
    get_race_info, get_site_type_info, get_structure_type_info,
    get_artifact_type_info, get_event_type_info
)

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/figures')
def figures():
    """List historical figures."""
    db = get_db()
    if not db:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Database not found'})
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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


@pages_bp.route('/figures/<int:figure_id>/affiliations')
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


@pages_bp.route('/sites')
def sites():
    """List sites."""
    db = get_db()
    if not db:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Database not found'})
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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


@pages_bp.route('/sites/<int:site_id>/structures')
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


@pages_bp.route('/map')
def world_map():
    """Display world map with sites."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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

    # Get rivers for overlay (only significant rivers with >= 5 segments)
    MIN_RIVER_SEGMENTS = 5
    rivers_list = []
    try:
        rivers_data = db.execute("SELECT name, path, end_pos FROM rivers").fetchall()
        for row in rivers_data:
            river = dict(row)
            path = river.get('path', '')
            if not path:
                continue
            # Parse path segments
            segments = []
            for segment in path.split('|'):
                if not segment.strip():
                    continue
                parts = segment.split(',')
                if len(parts) >= 4:
                    try:
                        x, y, width = int(parts[0]), int(parts[1]), int(parts[3])
                        segments.append({'x': x, 'y': y, 'w': width})
                    except ValueError:
                        continue
            # Only include rivers with enough segments
            if len(segments) >= MIN_RIVER_SEGMENTS:
                # Add end position
                end_pos = river.get('end_pos', '')
                if end_pos and ',' in end_pos:
                    try:
                        ex, ey = end_pos.split(',')
                        segments.append({'x': int(ex), 'y': int(ey), 'w': 4})
                    except ValueError:
                        pass
                rivers_list.append({
                    'name': river.get('name'),
                    'segments': segments
                })
    except Exception:
        pass  # Table may not exist

    # Get world constructions (roads, tunnels, bridges)
    roads_list = []
    try:
        roads_data = db.execute("SELECT name, type, coords FROM world_constructions").fetchall()
        for row in roads_data:
            road = dict(row)
            coords_str = road.get('coords', '')
            if not coords_str:
                continue
            points = []
            for pair in coords_str.split('|'):
                if ',' in pair:
                    try:
                        x, y = pair.split(',')[:2]
                        points.append({'x': int(x), 'y': int(y)})
                    except ValueError:
                        continue
            if points:
                roads_list.append({
                    'name': road.get('name'),
                    'type': road.get('type'),
                    'points': points
                })
    except Exception:
        pass  # Table may not exist

    # Get region boundaries for overlay
    regions_list = []
    try:
        regions_data = db.execute("SELECT id, name, type, coords FROM regions WHERE type != 'Ocean'").fetchall()
        for row in regions_data:
            region = dict(row)
            coords_str = region.get('coords', '')
            if not coords_str:
                continue
            # Parse coordinates into a set of tiles
            tiles = set()
            for pair in coords_str.split('|'):
                if ',' in pair:
                    try:
                        x, y = pair.split(',')[:2]
                        tiles.add((int(x), int(y)))
                    except ValueError:
                        continue
            if not tiles:
                continue
            # Find boundary edges (edges where adjacent tile is not in region)
            edges = []
            for (x, y) in tiles:
                # Check each of 4 sides
                if (x - 1, y) not in tiles:  # Left edge
                    edges.append({'x1': x, 'y1': y, 'x2': x, 'y2': y + 1})
                if (x + 1, y) not in tiles:  # Right edge
                    edges.append({'x1': x + 1, 'y1': y, 'x2': x + 1, 'y2': y + 1})
                if (x, y - 1) not in tiles:  # Top edge
                    edges.append({'x1': x, 'y1': y, 'x2': x + 1, 'y2': y})
                if (x, y + 1) not in tiles:  # Bottom edge
                    edges.append({'x1': x, 'y1': y + 1, 'x2': x + 1, 'y2': y + 1})
            if edges:
                regions_list.append({
                    'id': region.get('id'),
                    'name': region.get('name'),
                    'type': region.get('type'),
                    'edges': edges
                })
    except Exception:
        pass

    return render_template('map.html',
                         sites=sites_list,
                         peaks=peaks_list,
                         rivers=rivers_list,
                         roads=roads_list,
                         regions=regions_list,
                         min_x=min_x,
                         min_y=min_y,
                         map_width=map_width,
                         map_height=map_height,
                         type_counts=type_counts,
                         total_sites=len(sites_list),
                         total_peaks=len(peaks_list),
                         total_rivers=len(rivers_list),
                         total_roads=len([r for r in roads_list if r['type'] == 'road']),
                         total_regions=len(regions_list),
                         has_map=has_map,
                         world_id=world_id,
                         world=current_world)


@pages_bp.route('/map/search')
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


@pages_bp.route('/peak/<int:peak_id>')
def peak_detail(peak_id):
    """Display mountain peak details."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

    peak = db.execute(
        "SELECT * FROM mountain_peaks WHERE id = ?",
        [peak_id]
    ).fetchone()

    if not peak:
        flash('Peak not found.', 'error')
        return redirect(url_for('pages.world_map'))

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


@pages_bp.route('/events')
def events():
    """List historical events."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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


@pages_bp.route('/artifacts')
def artifacts():
    """List artifacts."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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


@pages_bp.route('/written')
def written_content():
    """List written content."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

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


@pages_bp.route('/graph')
def relations_graph():
    """Relations graph visualization page."""
    db = get_db()
    if not db:
        flash('Database not found. Run import first.', 'error')
        return redirect(url_for('worlds.index'))

    figure_id = request.args.get('figure', type=int)
    return render_template('graph.html', figure_id=figure_id)
