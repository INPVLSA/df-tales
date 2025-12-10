"""
API routes for DF Tales.
JSON endpoints for modals, search, graphs, and family trees.
"""

import json
from flask import Blueprint, request, jsonify

from db import get_db, get_current_year
from helpers import (
    get_race_info, get_site_type_info, get_structure_type_info,
    get_event_type_info, get_written_type_info
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/figures/search')
def figures_search():
    """Search figures by name for autocomplete."""
    db = get_db()
    if not db:
        return jsonify([])

    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)

    if len(q) < 2:
        return jsonify([])

    figures = db.execute("""
        SELECT id, name, race, caste FROM historical_figures
        WHERE name LIKE ? ORDER BY name LIMIT ?
    """, [f'%{q}%', limit]).fetchall()

    results = []
    for fig in figures:
        race_info = get_race_info(fig['race'], fig['caste'])
        results.append({
            'id': fig['id'],
            'name': fig['name'],
            'race': fig['race'],
            'race_label': race_info['label'],
            'race_img': race_info['img'],
            'race_icon': race_info['icon']
        })

    return jsonify(results)


@api_bp.route('/figure/<int:figure_id>')
def figure(figure_id):
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


@api_bp.route('/site/<int:site_id>')
def site(site_id):
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


@api_bp.route('/artifact/<int:artifact_id>')
def artifact(artifact_id):
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


@api_bp.route('/entity/<int:entity_id>')
def entity(entity_id):
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


@api_bp.route('/written/<int:written_id>')
def written(written_id):
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


@api_bp.route('/graph/<int:figure_id>')
def graph(figure_id):
    """Get relationship graph data for a figure."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    depth = request.args.get('depth', 1, type=int)
    depth = min(depth, 3)  # Limit depth to prevent huge graphs

    # Get the central figure
    central = db.execute("""
        SELECT id, name, race, caste FROM historical_figures WHERE id = ?
    """, [figure_id]).fetchone()

    if not central:
        return jsonify({'error': 'Figure not found'}), 404

    nodes = {}
    links = []
    visited = set()

    def add_figure(fig_id, current_depth):
        if fig_id in visited or current_depth > depth:
            return
        visited.add(fig_id)

        fig = db.execute("""
            SELECT id, name, race, caste, birth_year, death_year
            FROM historical_figures WHERE id = ?
        """, [fig_id]).fetchone()

        if not fig:
            return

        race_info = get_race_info(fig['race'], fig['caste'])
        nodes[fig_id] = {
            'id': fig_id,
            'name': fig['name'] or f"Figure #{fig_id}",
            'race': fig['race'],
            'race_label': race_info['label'],
            'race_img': race_info['img'],
            'alive': fig['death_year'] == -1,
            'depth': current_depth
        }

        if current_depth < depth:
            # Get relationships where this figure is source
            rels = db.execute("""
                SELECT target_hf as other_id, relationship, year
                FROM hf_relationships WHERE source_hf = ?
            """, [fig_id]).fetchall()

            for rel in rels:
                links.append({
                    'source': fig_id,
                    'target': rel['other_id'],
                    'type': rel['relationship'],
                    'year': rel['year']
                })
                add_figure(rel['other_id'], current_depth + 1)

            # Get relationships where this figure is target
            rels = db.execute("""
                SELECT source_hf as other_id, relationship, year
                FROM hf_relationships WHERE target_hf = ?
            """, [fig_id]).fetchall()

            for rel in rels:
                links.append({
                    'source': rel['other_id'],
                    'target': fig_id,
                    'type': rel['relationship'],
                    'year': rel['year']
                })
                add_figure(rel['other_id'], current_depth + 1)

    add_figure(figure_id, 0)

    # Deduplicate links
    seen_links = set()
    unique_links = []
    for link in links:
        key = (min(link['source'], link['target']), max(link['source'], link['target']), link['type'])
        if key not in seen_links:
            seen_links.add(key)
            unique_links.append(link)

    return jsonify({
        'nodes': list(nodes.values()),
        'links': unique_links,
        'central_id': figure_id
    })


@api_bp.route('/family-tree/<int:figure_id>')
def family_tree(figure_id):
    """Get family tree data for a figure (parents, siblings, spouses, children)."""
    db = get_db()
    if not db:
        return jsonify({'error': 'Database not found'}), 404

    def get_figure_data(fig_id):
        """Get figure info with race data."""
        fig = db.execute("""
            SELECT id, name, race, caste, birth_year, death_year
            FROM historical_figures WHERE id = ?
        """, [fig_id]).fetchone()
        if not fig:
            return None
        race_info = get_race_info(fig['race'], fig['caste'])
        return {
            'id': fig['id'],
            'name': fig['name'] or f"Figure #{fig['id']}",
            'race': fig['race'],
            'race_label': race_info['label'],
            'race_img': race_info['img'],
            'birth_year': fig['birth_year'],
            'death_year': fig['death_year'],
            'alive': fig['death_year'] == -1
        }

    # Get the central figure
    central = get_figure_data(figure_id)
    if not central:
        return jsonify({'error': 'Figure not found'}), 404

    # Get parents (where this figure has "mother" or "father" relationship TO someone)
    parents = []
    parent_rows = db.execute("""
        SELECT target_hf, relationship FROM hf_relationships
        WHERE source_hf = ? AND relationship IN ('mother', 'father')
    """, [figure_id]).fetchall()
    for row in parent_rows:
        parent = get_figure_data(row['target_hf'])
        if parent:
            parent['relation'] = row['relationship']
            parents.append(parent)

    # Get spouses (current and former)
    spouses = []
    spouse_rows = db.execute("""
        SELECT target_hf, relationship FROM hf_relationships
        WHERE source_hf = ? AND relationship IN ('spouse', 'former_spouse', 'deceased_spouse')
        UNION
        SELECT source_hf, relationship FROM hf_relationships
        WHERE target_hf = ? AND relationship IN ('spouse', 'former_spouse', 'deceased_spouse')
    """, [figure_id, figure_id]).fetchall()
    seen_spouses = set()
    for row in spouse_rows:
        if row['target_hf'] not in seen_spouses:
            spouse = get_figure_data(row['target_hf'])
            if spouse:
                spouse['relation'] = row['relationship']
                spouses.append(spouse)
                seen_spouses.add(row['target_hf'])

    # Get children (where someone has "mother" or "father" relationship TO this figure)
    children = []
    child_rows = db.execute("""
        SELECT source_hf FROM hf_relationships
        WHERE target_hf = ? AND relationship IN ('mother', 'father')
    """, [figure_id]).fetchall()
    seen_children = set()
    for row in child_rows:
        if row['source_hf'] not in seen_children:
            child = get_figure_data(row['source_hf'])
            if child:
                # Find other parent
                other_parent = db.execute("""
                    SELECT target_hf, relationship FROM hf_relationships
                    WHERE source_hf = ? AND relationship IN ('mother', 'father')
                    AND target_hf != ?
                """, [row['source_hf'], figure_id]).fetchone()
                if other_parent:
                    child['other_parent_id'] = other_parent['target_hf']
                children.append(child)
                seen_children.add(row['source_hf'])

    # Get siblings (share at least one parent)
    siblings = []
    if parents:
        parent_ids = [p['id'] for p in parents]
        sibling_rows = db.execute("""
            SELECT DISTINCT source_hf FROM hf_relationships
            WHERE target_hf IN ({}) AND relationship IN ('mother', 'father')
            AND source_hf != ?
        """.format(','.join('?' * len(parent_ids))), parent_ids + [figure_id]).fetchall()
        for row in sibling_rows:
            sibling = get_figure_data(row['source_hf'])
            if sibling:
                siblings.append(sibling)

    # Get grandparents
    grandparents = []
    for parent in parents:
        gp_rows = db.execute("""
            SELECT target_hf, relationship FROM hf_relationships
            WHERE source_hf = ? AND relationship IN ('mother', 'father')
        """, [parent['id']]).fetchall()
        for row in gp_rows:
            gp = get_figure_data(row['target_hf'])
            if gp:
                gp['relation'] = row['relationship']
                gp['through'] = parent['id']
                grandparents.append(gp)

    # Get grandchildren
    grandchildren = []
    for child in children:
        gc_rows = db.execute("""
            SELECT source_hf FROM hf_relationships
            WHERE target_hf = ? AND relationship IN ('mother', 'father')
        """, [child['id']]).fetchall()
        for row in gc_rows:
            gc = get_figure_data(row['source_hf'])
            if gc:
                gc['through'] = child['id']
                grandchildren.append(gc)

    return jsonify({
        'central': central,
        'parents': parents,
        'grandparents': grandparents,
        'spouses': spouses,
        'children': children,
        'grandchildren': grandchildren,
        'siblings': siblings
    })
