"""
Helper functions for DF Tales.
Type info getters and formatters for races, sites, structures, artifacts, events.
"""

import json
from pathlib import Path
from markupsafe import Markup

from data.mappings import (
    RACE_DATA, RACE_PATTERNS, RACE_ICONS_DIR,
    SITE_TYPE_DATA, SITE_ICONS_DIR,
    STRUCTURE_TYPE_DATA, STRUCTURE_ICONS_DIR,
    ARTIFACT_TYPE_DATA, ARTIFACT_ICONS_DIR,
    MATERIAL_COLORS, MATERIAL_CATEGORY_PATTERNS,
    EVENT_TYPE_DATA, WRITTEN_TYPE_COLORS,
)
from db import get_db


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
    """Format event details into a human-readable description with clickable links."""
    db = get_db()

    # Helper to create entity links
    def hf_link(hfid):
        if not hfid or not db:
            return f"HF#{hfid}" if hfid else "?"
        row = db.execute("SELECT name FROM historical_figures WHERE id = ?", [hfid]).fetchone()
        name = row['name'].title() if row and row['name'] else f"HF#{hfid}"
        return f"<a href='#' class='entity-link' data-type='figure' data-id='{hfid}'>{name}</a>"

    def site_link(site_id):
        if not site_id or not db:
            return f"Site#{site_id}" if site_id else "?"
        row = db.execute("SELECT name FROM sites WHERE id = ?", [site_id]).fetchone()
        name = row['name'].title() if row and row['name'] else f"Site#{site_id}"
        return f"<a href='#' class='entity-link' data-type='site' data-id='{site_id}'>{name}</a>"

    def entity_link(entity_id):
        if not entity_id or not db:
            return f"Entity#{entity_id}" if entity_id else "?"
        row = db.execute("SELECT name FROM entities WHERE id = ?", [entity_id]).fetchone()
        name = row['name'].title() if row and row['name'] else f"Entity#{entity_id}"
        return f"<a href='#' class='entity-link' data-type='entity' data-id='{entity_id}'>{name}</a>"

    def artifact_link(artifact_id):
        if not artifact_id or not db:
            return f"Artifact#{artifact_id}" if artifact_id else "?"
        row = db.execute("SELECT name FROM artifacts WHERE id = ?", [artifact_id]).fetchone()
        name = row['name'].title() if row and row['name'] else f"Artifact#{artifact_id}"
        return f"<a href='#' class='entity-link' data-type='artifact' data-id='{artifact_id}'>{name}</a>"

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
                parts.append(f"{hf_link(hfid)} established a lair at {site_link(site_id)}")
            elif link_type == 'home_site_realization_building':
                parts.append(f"{hf_link(hfid)} moved into building at {site_link(site_id)}")
            elif link_type == 'seat_of_power':
                parts.append(f"{hf_link(hfid)} claimed seat of power at {site_link(site_id)}")
            elif link_type == 'occupation':
                parts.append(f"{hf_link(hfid)} occupied {site_link(site_id)}")
            elif link_type == 'home_site_abstract_building':
                parts.append(f"{hf_link(hfid)} took residence at {site_link(site_id)}")
            elif link_type == 'hangout':
                parts.append(f"{hf_link(hfid)} started hanging out at {site_link(site_id)}")
            else:
                parts.append(f"{hf_link(hfid)} linked to {site_link(site_id)} ({link_type.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>{site_link(site_id)}</span>")

    elif normalized_type == 'remove_hf_site_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            parts.append(f"{hf_link(hfid)} left {site_link(site_id)} ({link_type.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>{site_link(site_id)}</span>")

    elif normalized_type == 'add_hf_entity_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            if link_type == 'member':
                parts.append(f"{hf_link(hfid)} joined {entity_link(civ_id)}")
            elif link_type == 'position':
                position = extra.get('position', 'a position')
                parts.append(f"{hf_link(hfid)} took {position} in {entity_link(civ_id)}")
            elif link_type == 'former member':
                parts.append(f"{hf_link(hfid)} was former member of {entity_link(civ_id)}")
            elif link_type == 'prisoner':
                parts.append(f"{hf_link(hfid)} imprisoned by {entity_link(civ_id)}")
            elif link_type == 'enemy':
                parts.append(f"{hf_link(hfid)} became enemy of {entity_link(civ_id)}")
            elif link_type == 'slave':
                parts.append(f"{hf_link(hfid)} enslaved by {entity_link(civ_id)}")
            else:
                parts.append(f"{hf_link(hfid)} linked to {entity_link(civ_id)} ({link_type.replace('_', ' ')})")
        elif civ_id:
            parts.append(f"<span class='detail-limited'>{entity_link(civ_id)}</span>")

    elif normalized_type == 'remove_hf_entity_link':
        link_type = extra.get('link_type')
        if hfid and link_type:
            parts.append(f"{hf_link(hfid)} left {entity_link(civ_id)} ({link_type.replace('_', ' ')})")
        elif civ_id:
            parts.append(f"<span class='detail-limited'>{entity_link(civ_id)}</span>")

    elif normalized_type == 'hist_figure_died':
        cause = event['death_cause'] or extra.get('death_cause')
        slayer = event['slayer_hfid'] or extra.get('slayer_hfid')
        if hfid:
            if slayer:
                parts.append(f"{hf_link(hfid)} killed by {hf_link(slayer)}")
            else:
                parts.append(f"{hf_link(hfid)} died")
            if cause:
                parts.append(f"({cause.replace('_', ' ')})")
            if site_id:
                parts.append(f"at {site_link(site_id)}")
        elif site_id:
            parts.append(f"<span class='detail-limited'>{site_link(site_id)}</span>")

    elif normalized_type == 'add_hf_hf_link':
        hfid1 = extra.get('hfid1') or extra.get('hf') or hfid
        hfid2 = extra.get('hfid2') or extra.get('hf_target')
        link_type = extra.get('link_type')
        if hfid1 and hfid2:
            rel = link_type.replace('_', ' ') if link_type else 'relationship'
            parts.append(f"{hf_link(hfid1)} and {hf_link(hfid2)} formed {rel}")
        else:
            parts.append("<span class='detail-limited'>-</span>")

    elif normalized_type == 'artifact_created':
        art_id = event['artifact_id'] or extra.get('artifact_id')
        if hfid and art_id:
            parts.append(f"{hf_link(hfid)} created {artifact_link(art_id)}")
            if site_id:
                parts.append(f"at {site_link(site_id)}")
        elif art_id:
            parts.append(f"{artifact_link(art_id)} created")
            if site_id:
                parts.append(f"at {site_link(site_id)}")
        else:
            parts.append("<span class='detail-limited'>-</span>")

    elif normalized_type == 'change_hf_state':
        state = event['state'] or extra.get('state')
        reason = event['reason'] or extra.get('reason')
        if hfid and state:
            parts.append(f"{hf_link(hfid)} became {state.replace('_', ' ')}")
            if site_id:
                parts.append(f"at {site_link(site_id)}")
            if reason:
                parts.append(f"({reason.replace('_', ' ')})")
        elif site_id:
            parts.append(f"<span class='detail-limited'>{site_link(site_id)}</span>")

    elif normalized_type == 'change_hf_job':
        new_job = extra.get('new_job')
        old_job = extra.get('old_job')
        if hfid and new_job:
            if old_job:
                parts.append(f"{hf_link(hfid)} changed from {old_job.replace('_', ' ')} to {new_job.replace('_', ' ')}")
            else:
                parts.append(f"{hf_link(hfid)} became {new_job.replace('_', ' ')}")
            if site_id:
                parts.append(f"at {site_link(site_id)}")
        elif site_id:
            parts.append(f"<span class='detail-limited'>{site_link(site_id)}</span>")

    elif normalized_type == 'created_site':
        site_civ_id = extra.get('site_civ_id')
        if civ_id and site_id:
            parts.append(f"{entity_link(civ_id)} founded {site_link(site_id)}")
        elif site_id:
            parts.append(f"{site_link(site_id)} founded")

    elif normalized_type == 'created_building' or normalized_type == 'created_structure':
        structure_id = event['structure_id'] or extra.get('structure_id')
        if hfid and structure_id:
            parts.append(f"{hf_link(hfid)} built Structure#{structure_id}")
        elif structure_id:
            parts.append(f"Structure#{structure_id} built")
        if site_id:
            parts.append(f"at {site_link(site_id)}")

    elif normalized_type == 'hf_destroyed_site':
        if hfid and site_id:
            parts.append(f"{hf_link(hfid)} destroyed {site_link(site_id)}")
        elif site_id:
            parts.append(f"{site_link(site_id)} destroyed")

    elif normalized_type == 'hf_attacked_site':
        if hfid and site_id:
            parts.append(f"{hf_link(hfid)} attacked {site_link(site_id)}")
        elif site_id:
            parts.append(f"{site_link(site_id)} attacked")

    else:
        # Generic fallback - show available IDs with links
        shown = []
        if hfid:
            shown.append(hf_link(hfid))
        if site_id:
            shown.append(site_link(site_id))
        if civ_id:
            shown.append(entity_link(civ_id))
        if entity_id and entity_id != civ_id:
            shown.append(entity_link(entity_id))
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
