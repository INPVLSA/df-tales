#!/usr/bin/env python3
"""
DF-World XML Import Script
Imports Dwarf Fortress legends XML data into SQLite database.
"""

import os
import re
import json
import sqlite3
import tempfile
import hashlib
from pathlib import Path
from lxml import etree

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
WORLDS_DIR = DATA_DIR / "worlds"
MASTER_DB_PATH = DATA_DIR / "master.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
MASTER_SCHEMA_PATH = BASE_DIR / "master_schema.sql"

# XML files (user should place these in the base directory)
LEGENDS_FILE = None
LEGENDS_PLUS_FILE = None


def find_xml_files(legends_path=None, plus_path=None):
    """Find or set legends XML files. legends_plus is optional."""
    global LEGENDS_FILE, LEGENDS_PLUS_FILE

    # If paths provided via arguments, use them
    if legends_path:
        LEGENDS_FILE = Path(legends_path)
        if plus_path:
            LEGENDS_PLUS_FILE = Path(plus_path)
        return LEGENDS_FILE.exists()

    # Otherwise, search in base directory
    for f in BASE_DIR.glob("*.xml"):
        name = f.name.lower()
        if "legends_plus" in name:
            LEGENDS_PLUS_FILE = f
        elif "legends" in name:
            LEGENDS_FILE = f

    # Only legends.xml is required, legends_plus is optional
    return LEGENDS_FILE is not None


def sanitize_xml_file(filepath):
    """
    Remove invalid XML 1.0 characters and return path to sanitized temp file.
    Processes in chunks to handle large files.
    Also converts CP437 encoding declaration to UTF-8.
    """
    print(f"  Sanitizing {filepath.name}...")

    # Pattern for invalid XML 1.0 chars (control chars except tab, newline, CR)
    invalid_chars = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
    # Pattern to fix encoding declaration
    encoding_pattern = re.compile(r'encoding=["\']CP437["\']', re.IGNORECASE)

    temp_fd, temp_path = tempfile.mkstemp(suffix='.xml')
    first_chunk = True

    with open(filepath, 'rb') as infile, os.fdopen(temp_fd, 'wb') as outfile:
        while True:
            chunk = infile.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            # Decode from CP437, sanitize, encode as UTF-8
            text = chunk.decode('cp437', errors='replace')
            text = invalid_chars.sub('', text)
            # Fix encoding declaration in first chunk
            if first_chunk:
                text = encoding_pattern.sub('encoding="UTF-8"', text)
                first_chunk = False
            outfile.write(text.encode('utf-8'))

    print("  Sanitization complete.")
    return temp_path


def xml_to_dict(element):
    """Convert an XML element to a dictionary."""
    result = {}

    for child in element:
        tag = child.tag

        if len(child):
            # Has children - recurse
            value = xml_to_dict(child)
        else:
            # Leaf node
            value = child.text or ''

        if tag in result:
            # Multiple elements with same tag - make list
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value

    return result


def stream_elements(filepath, tag, callback, report_every=10000):
    """
    Stream XML file and call callback for each element with given tag.
    Uses iterparse for memory efficiency.
    """
    count = 0
    context = etree.iterparse(filepath, events=('end',), tag=tag)

    for event, elem in context:
        data = xml_to_dict(elem)
        callback(data)
        count += 1

        if count % report_every == 0:
            print(f"    Processed {count} {tag} records...")

        # Clear element to free memory
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    del context
    return count


def get_world_info(filepath):
    """Extract world name and altname from XML file.

    Looks for <name> and <altname> as direct children of <df_world>.
    """
    name = altname = None
    depth = 0

    context = etree.iterparse(filepath, events=('start', 'end'))
    for event, elem in context:
        if event == 'start':
            depth += 1
        elif event == 'end':
            # depth 2 means direct child of root (df_world is depth 1)
            if depth == 2:
                if elem.tag == 'name' and name is None:
                    name = elem.text
                elif elem.tag == 'altname' and altname is None:
                    altname = elem.text
            depth -= 1
            elem.clear()
            # Stop once we have both or hit a deeper section
            if (name and altname) or depth == 1 and elem.tag in ('regions', 'sites', 'artifacts'):
                break

    del context
    return name, altname


def get_world_info_from_legends(filepath):
    """Extract world name from legends.xml (no altname available).

    Looks for <name> as direct child of <df_world>.
    """
    name = None
    depth = 0

    context = etree.iterparse(filepath, events=('start', 'end'))
    for event, elem in context:
        if event == 'start':
            depth += 1
        elif event == 'end':
            # depth 2 means direct child of root
            if depth == 2 and elem.tag == 'name' and name is None:
                name = elem.text
                elem.clear()
                break
            depth -= 1
            elem.clear()

    del context
    return name, None


def init_master_db():
    """Initialize master database for tracking worlds."""
    DATA_DIR.mkdir(exist_ok=True)
    WORLDS_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(MASTER_DB_PATH)
    conn.row_factory = sqlite3.Row

    with open(MASTER_SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # Migration: add has_plus column if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(worlds)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'has_plus' not in columns:
        cursor.execute("ALTER TABLE worlds ADD COLUMN has_plus INTEGER DEFAULT 0")
        conn.commit()

    return conn


def generate_world_id(name):
    """Generate a unique ID for a world based on name and timestamp."""
    import time
    raw = f"{name or 'unknown'}_{time.time()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def register_world(name, altname, db_path, has_plus=False):
    """Register a world in the master database and set it as current."""
    conn = init_master_db()
    cursor = conn.cursor()

    # Use fallback name if none provided (vanilla legends.xml has no world name)
    display_name = name or "Unknown World"
    world_id = generate_world_id(name)

    # Unset any current world
    cursor.execute("UPDATE worlds SET is_current = 0 WHERE is_current = 1")

    # Insert new world as current
    cursor.execute(
        "INSERT INTO worlds (id, name, altname, db_path, is_current, has_plus) VALUES (?, ?, ?, ?, 1, ?)",
        (world_id, display_name, altname, str(db_path), 1 if has_plus else 0)
    )

    conn.commit()
    conn.close()

    return world_id


def update_world_has_plus(world_id):
    """Mark a world as having legends_plus data."""
    conn = init_master_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE worlds SET has_plus = 1 WHERE id = ?", (world_id,))
    conn.commit()
    conn.close()


def init_world_db(db_path):
    """Initialize a world database with schema."""
    # Ensure worlds directory exists
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Read and execute schema
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    return conn


def run_import(legends_path=None, plus_path=None):
    """Main import function."""
    print("=" * 50)
    print("DF-World XML Import")
    print("=" * 50)

    # Find XML files
    if not find_xml_files(legends_path, plus_path):
        print("\nERROR: Could not find XML files!")
        print("Please place your legends XML file in:", BASE_DIR)
        print("Expected: *legends.xml (required)")
        print("Optional: *legends_plus.xml (DFHack export for additional data)")
        return False

    has_plus = LEGENDS_PLUS_FILE is not None

    print(f"\nUsing XML files:")
    print(f"  Legends: {LEGENDS_FILE}")
    if has_plus:
        print(f"  Legends+: {LEGENDS_PLUS_FILE}")
    else:
        print("  Legends+: Not provided (some features will be limited)")

    # Sanitize XML files
    print("\nSanitizing XML files...")
    legends_clean = sanitize_xml_file(LEGENDS_FILE)
    legends_plus_clean = sanitize_xml_file(LEGENDS_PLUS_FILE) if has_plus else None

    try:
        # First, get world info to determine database name
        print("\nReading world info...")
        if has_plus:
            name, altname = get_world_info(legends_plus_clean)
        else:
            name, altname = get_world_info_from_legends(legends_clean)
        print(f"  World: {name}" + (f" ({altname})" if altname else ""))

        # Generate world ID and database path
        world_id = generate_world_id(name)
        db_path = WORLDS_DIR / f"{world_id}.db"

        # Initialize world database
        print(f"\nInitializing database: {db_path.name}")
        conn = init_world_db(db_path)
        cursor = conn.cursor()

        # Insert world info (use fallback if no name from vanilla legends.xml)
        cursor.execute("INSERT INTO world (name, altname) VALUES (?, ?)", (name or "Unknown World", altname))
        conn.commit()

        # === LEGENDS.XML ===
        print("\n--- Processing legends.xml ---")

        # Regions
        print("\nImporting regions...")
        def import_region(data):
            cursor.execute(
                "INSERT OR REPLACE INTO regions (id, name, type) VALUES (?, ?, ?)",
                (data.get('id'), data.get('name'), data.get('type'))
            )
        count = stream_elements(legends_clean, 'region', import_region)
        conn.commit()
        print(f"  Imported {count} regions.")

        # Underground regions
        print("\nImporting underground regions...")
        def import_underground(data):
            cursor.execute(
                "INSERT OR REPLACE INTO underground_regions (id, type, depth) VALUES (?, ?, ?)",
                (data.get('id'), data.get('type'), data.get('depth'))
            )
        count = stream_elements(legends_clean, 'underground_region', import_underground)
        conn.commit()
        print(f"  Imported {count} underground regions.")

        # Sites
        print("\nImporting sites...")
        def import_site(data):
            cursor.execute(
                "INSERT OR REPLACE INTO sites (id, name, type, coords, rectangle) VALUES (?, ?, ?, ?, ?)",
                (data.get('id'), data.get('name'), data.get('type'), data.get('coords'), data.get('rectangle'))
            )
        count = stream_elements(legends_clean, 'site', import_site)
        conn.commit()
        print(f"  Imported {count} sites.")

        # Artifacts
        print("\nImporting artifacts...")
        def import_artifact(data):
            cursor.execute(
                """INSERT OR REPLACE INTO artifacts
                   (id, name, item_type, item_subtype, mat, creator_hfid, site_id, holder_hfid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (data.get('id'), data.get('name') or data.get('name_string'),
                 data.get('item_type'), data.get('item_subtype'), data.get('mat'),
                 data.get('creator_hfid'), data.get('site_id'), data.get('holder_hfid'))
            )
        count = stream_elements(legends_clean, 'artifact', import_artifact)
        conn.commit()
        print(f"  Imported {count} artifacts.")

        # === LEGENDS_PLUS.XML (optional) ===
        if has_plus:
            print("\n--- Processing legends_plus.xml ---")

            # Update regions with coordinates and evilness from legends_plus
            print("\nUpdating regions with coordinates and evilness...")
            def update_region_data(data):
                region_id = data.get('id')
                coords = data.get('coords')
                evilness = data.get('evilness')
                if region_id is not None:
                    cursor.execute(
                        "UPDATE regions SET coords = ?, evilness = ? WHERE id = ?",
                        (coords, evilness, region_id)
                    )
            count = stream_elements(legends_plus_clean, 'region', update_region_data)
            conn.commit()
            print(f"  Updated {count} regions with coordinates and evilness.")

            # Landmasses
            print("\nImporting landmasses...")
            def import_landmass(data):
                cursor.execute(
                    "INSERT INTO landmasses (id, name, coord_1, coord_2) VALUES (?, ?, ?, ?)",
                    (data.get('id'), data.get('name'), data.get('coord_1'), data.get('coord_2'))
                )
            count = stream_elements(legends_plus_clean, 'landmass', import_landmass)
            conn.commit()
            print(f"  Imported {count} landmasses.")

            # Mountain peaks
            print("\nImporting mountain peaks...")
            def import_peak(data):
                cursor.execute(
                    "INSERT INTO mountain_peaks (id, name, coords, height, is_volcano) VALUES (?, ?, ?, ?, ?)",
                    (data.get('id'), data.get('name'), data.get('coords'),
                     data.get('height'), 1 if 'is_volcano' in data else 0)
                )
            count = stream_elements(legends_plus_clean, 'mountain_peak', import_peak)
            conn.commit()
            print(f"  Imported {count} mountain peaks.")

            # Update sites + structures
            print("\nUpdating sites and importing structures...")
            structure_count = 0
            def import_site_plus(data):
                nonlocal structure_count
                site_id = data.get('id')
                if site_id:
                    cursor.execute(
                        "UPDATE sites SET civ_id = ?, cur_owner_id = ? WHERE id = ?",
                        (data.get('civ_id'), data.get('cur_owner_id'), site_id)
                    )

                    # Structures
                    structures = data.get('structures', {})
                    if isinstance(structures, dict):
                        struct_list = structures.get('structure', [])
                        if isinstance(struct_list, dict):
                            struct_list = [struct_list]
                        for struct in struct_list:
                            if isinstance(struct, dict):
                                cursor.execute(
                                    "INSERT INTO structures (local_id, site_id, name, name2, type) VALUES (?, ?, ?, ?, ?)",
                                    (struct.get('id'), site_id, struct.get('name'), struct.get('name2'), struct.get('type'))
                                )
                                structure_count += 1
            count = stream_elements(legends_plus_clean, 'site', import_site_plus)
            conn.commit()
            print(f"  Updated {count} sites, imported {structure_count} structures.")

            # Entities
            print("\nImporting entities...")
            pos_count = assign_count = 0
            debug_shown = False
            def import_entity(data):
                nonlocal pos_count, assign_count, debug_shown
                if not debug_shown:
                    print(f"  DEBUG - Sample entity keys: {list(data.keys())}")
                    debug_shown = True
                entity_id = data.get('id')
                cursor.execute(
                    "INSERT OR REPLACE INTO entities (id, name, race, type) VALUES (?, ?, ?, ?)",
                    (entity_id, data.get('name'), data.get('race'), data.get('type'))
                )

                # Positions
                positions = data.get('entity_position', [])
                if isinstance(positions, dict):
                    positions = [positions]
                for pos in positions:
                    if isinstance(pos, dict):
                        cursor.execute(
                            "INSERT INTO entity_positions (entity_id, position_id, name) VALUES (?, ?, ?)",
                            (entity_id, pos.get('id'), pos.get('name'))
                        )
                        pos_count += 1

                # Assignments
                assignments = data.get('entity_position_assignment', [])
                if isinstance(assignments, dict):
                    assignments = [assignments]
                for assign in assignments:
                    if isinstance(assign, dict):
                        cursor.execute(
                            "INSERT INTO entity_position_assignments (entity_id, position_id, histfig_id) VALUES (?, ?, ?)",
                            (entity_id, assign.get('position_id'), assign.get('histfig'))
                        )
                        assign_count += 1
            count = stream_elements(legends_plus_clean, 'entity', import_entity)
            conn.commit()
            print(f"  Imported {count} entities, {pos_count} positions, {assign_count} assignments.")
        else:
            print("\n--- Skipping legends_plus.xml data (file not found) ---")
            print("  Skipped: landmasses, mountain peaks, structures, entities")

        # Historical figures (from legends.xml which has names)
        print("\nImporting historical figures from legends.xml...")
        entity_link_count = site_link_count = 0
        def import_hf(data):
            nonlocal entity_link_count, site_link_count
            hfid = data.get('id')
            cursor.execute(
                "INSERT OR REPLACE INTO historical_figures (id, name, race, caste, sex, birth_year, death_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (hfid, data.get('name'), data.get('race'), data.get('caste'),
                 data.get('sex'), data.get('birth_year'), data.get('death_year'))
            )

            # Entity links
            links = data.get('entity_link', [])
            if isinstance(links, dict):
                links = [links]
            for link in links:
                if isinstance(link, dict):
                    cursor.execute(
                        "INSERT INTO hf_entity_links (hfid, entity_id, link_type, link_strength) VALUES (?, ?, ?, ?)",
                        (hfid, link.get('entity_id'), link.get('link_type'), link.get('link_strength'))
                    )
                    entity_link_count += 1

            # Site links
            slinks = data.get('site_link', [])
            if isinstance(slinks, dict):
                slinks = [slinks]
            for slink in slinks:
                if isinstance(slink, dict):
                    cursor.execute(
                        "INSERT INTO hf_site_links (hfid, site_id, link_type) VALUES (?, ?, ?)",
                        (hfid, slink.get('site_id'), slink.get('link_type'))
                    )
                    site_link_count += 1
        count = stream_elements(legends_clean, 'historical_figure', import_hf)
        conn.commit()
        print(f"  Imported {count} historical figures, {entity_link_count} entity links, {site_link_count} site links.")

        # Relationships (legends_plus only)
        if has_plus:
            print("\nImporting relationships...")
            def import_rel(data):
                cursor.execute(
                    "INSERT OR IGNORE INTO hf_relationships (source_hf, target_hf, relationship, year) VALUES (?, ?, ?, ?)",
                    (data.get('source_hf'), data.get('target_hf'), data.get('relationship'), data.get('year'))
                )
            count = stream_elements(legends_plus_clean, 'historical_event_relationship', import_rel)
            conn.commit()
            print(f"  Imported {count} relationships.")

        # Historical events
        print("\nImporting historical events...")
        if has_plus:
            # First get years from legends.xml (legends_plus doesn't have them)
            event_years = {}
            def collect_years(data):
                event_id = data.get('id')
                year = data.get('year')
                if event_id is not None and year is not None:
                    event_years[int(event_id)] = int(year)
            stream_elements(legends_clean, 'historical_event', collect_years)
            print(f"  Collected years for {len(event_years)} events from legends.xml")

            # Now import full event data from legends_plus.xml with years
            known_fields = {'id', 'year', 'type', 'site_id', 'site', 'hfid', 'civ_id', 'civ',
                           'state', 'reason', 'slayer_hfid', 'slayer_hf', 'death_cause',
                           'artifact_id', 'entity_id', 'structure_id'}
            def import_event_plus(data):
                event_id = data.get('id')
                year = event_years.get(int(event_id)) if event_id is not None else None
                extra = {k: v for k, v in data.items() if k not in known_fields}
                cursor.execute(
                    """INSERT INTO historical_events
                       (id, year, type, site_id, hfid, civ_id, state, reason, slayer_hfid,
                        death_cause, artifact_id, entity_id, structure_id, extra_data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, year, data.get('type'),
                     data.get('site_id') or data.get('site'), data.get('hfid'),
                     data.get('civ_id') or data.get('civ'), data.get('state'), data.get('reason'),
                     data.get('slayer_hfid') or data.get('slayer_hf'), data.get('death_cause'),
                     data.get('artifact_id'), data.get('entity_id'), data.get('structure_id'),
                     json.dumps(extra) if extra else None)
                )
            count = stream_elements(legends_plus_clean, 'historical_event', import_event_plus)
        else:
            # Import events from legends.xml only (less detailed but has year)
            basic_known_fields = {'id', 'year', 'type', 'site_id', 'hfid', 'civ_id',
                                  'slayer_hfid', 'death_cause', 'artifact_id', 'entity_id', 'structure_id'}
            def import_event_basic(data):
                # Extract simple values, handling cases where field might be a dict/list
                def safe_get(key):
                    val = data.get(key)
                    if isinstance(val, (dict, list)):
                        return None
                    return val

                # Collect extra fields
                extra = {}
                for k, v in data.items():
                    if k not in basic_known_fields:
                        if isinstance(v, (str, int, float)) or v is None:
                            extra[k] = v

                cursor.execute(
                    """INSERT INTO historical_events
                       (id, year, type, site_id, hfid, civ_id, slayer_hfid,
                        death_cause, artifact_id, entity_id, structure_id, extra_data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (safe_get('id'), safe_get('year'), safe_get('type'),
                     safe_get('site_id'), safe_get('hfid'), safe_get('civ_id'),
                     safe_get('slayer_hfid'), safe_get('death_cause'),
                     safe_get('artifact_id'), safe_get('entity_id'), safe_get('structure_id'),
                     json.dumps(extra) if extra else None)
                )
            count = stream_elements(legends_clean, 'historical_event', import_event_basic)
        conn.commit()
        print(f"  Imported {count} historical events.")

        # Update artifacts from legends_plus (has more detail)
        if has_plus:
            print("\nUpdating artifacts from legends_plus...")
            def update_artifact_plus(data):
                cursor.execute(
                    """UPDATE artifacts SET
                       item_type = COALESCE(?, item_type),
                       item_subtype = COALESCE(?, item_subtype),
                       mat = COALESCE(?, mat)
                       WHERE id = ?""",
                    (data.get('item_type'), data.get('item_subtype'), data.get('mat'),
                     data.get('id'))
                )
            count = stream_elements(legends_plus_clean, 'artifact', update_artifact_plus)
            conn.commit()
            print(f"  Updated {count} artifacts.")

        # Populate artifact creator/site from artifact_created events
        print("\nPopulating artifact creators from events...")
        cursor.execute("""
            UPDATE artifacts SET
                creator_hfid = (
                    SELECT CASE
                        WHEN json_extract(e.extra_data, '$.creator_hfid') IS NOT NULL
                             AND json_extract(e.extra_data, '$.creator_hfid') != '-1'
                        THEN json_extract(e.extra_data, '$.creator_hfid')
                        ELSE e.hfid
                    END
                    FROM historical_events e
                    WHERE e.type = 'artifact_created' AND e.artifact_id = artifacts.id
                    LIMIT 1
                ),
                site_id = (
                    SELECT e.site_id
                    FROM historical_events e
                    WHERE e.type = 'artifact_created' AND e.artifact_id = artifacts.id
                    AND e.site_id IS NOT NULL AND e.site_id != -1
                    LIMIT 1
                )
            WHERE EXISTS (
                SELECT 1 FROM historical_events e
                WHERE e.type = 'artifact_created' AND e.artifact_id = artifacts.id
            )
        """)
        conn.commit()
        print(f"  Updated {cursor.rowcount} artifacts with creator/site info.")

        # Written content (legends_plus only)
        if has_plus:
            print("\nImporting written content...")
            style_count = ref_count = 0
            def import_content(data):
                nonlocal style_count, ref_count
                content_id = data.get('id')
                cursor.execute(
                    "INSERT INTO written_content (id, title, type, author_hfid, page_start, page_end) VALUES (?, ?, ?, ?, ?, ?)",
                    (content_id, data.get('title'), data.get('type'), data.get('author'),
                     data.get('page_start'), data.get('page_end'))
                )

                # Styles
                styles = data.get('style', [])
                if isinstance(styles, str):
                    styles = [styles]
                for style in styles:
                    cursor.execute(
                        "INSERT INTO written_content_styles (written_content_id, style) VALUES (?, ?)",
                        (content_id, style)
                    )
                    style_count += 1

                # References
                refs = data.get('reference', [])
                if isinstance(refs, dict):
                    refs = [refs]
                for ref in refs:
                    if isinstance(ref, dict):
                        cursor.execute(
                            "INSERT INTO written_content_references (written_content_id, ref_type, ref_id) VALUES (?, ?, ?)",
                            (content_id, ref.get('type'), ref.get('id'))
                        )
                        ref_count += 1
            count = stream_elements(legends_plus_clean, 'written_content', import_content)
            conn.commit()
            print(f"  Imported {count} written content, {style_count} styles, {ref_count} references.")

        conn.close()

        # Register world in master database
        print("\nRegistering world...")
        register_world(name, altname, db_path, has_plus=has_plus)
        print(f"  World ID: {world_id}")
        print(f"  Has legends_plus: {'Yes' if has_plus else 'No'}")

        print("\n" + "=" * 50)
        print("Import complete!")
        print(f"World '{name}' is now active.")
        print("=" * 50)
        return True

    finally:
        # Cleanup temp files
        os.unlink(legends_clean)
        if legends_plus_clean:
            os.unlink(legends_plus_clean)


def run_merge_plus(world_id, db_path, plus_path):
    """Merge legends_plus.xml data into an existing world database."""
    print("=" * 50)
    print("DF-World Legends Plus Merge")
    print("=" * 50)

    plus_file = Path(plus_path)
    if not plus_file.exists():
        print(f"\nERROR: File not found: {plus_path}")
        return False

    print(f"\nMerging into world: {world_id}")
    print(f"  Database: {db_path}")
    print(f"  Legends+: {plus_file}")

    # Sanitize XML file
    print("\nSanitizing XML file...")
    legends_plus_clean = sanitize_xml_file(plus_file)

    try:
        # Connect to existing world database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Get world info from legends_plus
        print("\nReading world info...")
        name, altname = get_world_info(legends_plus_clean)
        print(f"  World: {name}" + (f" ({altname})" if altname else ""))

        # Update world name and altname from plus data
        if name:
            cursor.execute("UPDATE world SET name = ? WHERE name IS NULL OR name = '' OR name = 'Unknown World'", (name,))
        if altname:
            cursor.execute("UPDATE world SET altname = ? WHERE altname IS NULL", (altname,))
        conn.commit()

        print("\n--- Processing legends_plus.xml ---")

        # Update regions with coordinates and evilness from legends_plus
        print("\nUpdating regions with coordinates and evilness...")
        def update_region_data(data):
            region_id = data.get('id')
            coords = data.get('coords')
            evilness = data.get('evilness')
            if region_id is not None:
                cursor.execute(
                    "UPDATE regions SET coords = ?, evilness = ? WHERE id = ?",
                    (coords, evilness, region_id)
                )
        count = stream_elements(legends_plus_clean, 'region', update_region_data)
        conn.commit()
        print(f"  Updated {count} regions with coordinates and evilness.")

        # Landmasses
        print("\nImporting landmasses...")
        def import_landmass(data):
            cursor.execute(
                "INSERT OR REPLACE INTO landmasses (id, name, coord_1, coord_2) VALUES (?, ?, ?, ?)",
                (data.get('id'), data.get('name'), data.get('coord_1'), data.get('coord_2'))
            )
        count = stream_elements(legends_plus_clean, 'landmass', import_landmass)
        conn.commit()
        print(f"  Imported {count} landmasses.")

        # Mountain peaks
        print("\nImporting mountain peaks...")
        def import_peak(data):
            cursor.execute(
                "INSERT OR REPLACE INTO mountain_peaks (id, name, coords, height, is_volcano) VALUES (?, ?, ?, ?, ?)",
                (data.get('id'), data.get('name'), data.get('coords'),
                 data.get('height'), 1 if 'is_volcano' in data else 0)
            )
        count = stream_elements(legends_plus_clean, 'mountain_peak', import_peak)
        conn.commit()
        print(f"  Imported {count} mountain peaks.")

        # Update sites + structures
        print("\nUpdating sites and importing structures...")
        structure_count = 0
        def import_site_plus(data):
            nonlocal structure_count
            site_id = data.get('id')
            if site_id:
                cursor.execute(
                    "UPDATE sites SET civ_id = ?, cur_owner_id = ? WHERE id = ?",
                    (data.get('civ_id'), data.get('cur_owner_id'), site_id)
                )

                # Structures
                structures = data.get('structures', {})
                if isinstance(structures, dict):
                    struct_list = structures.get('structure', [])
                    if isinstance(struct_list, dict):
                        struct_list = [struct_list]
                    for struct in struct_list:
                        if isinstance(struct, dict):
                            cursor.execute(
                                "INSERT OR REPLACE INTO structures (local_id, site_id, name, name2, type) VALUES (?, ?, ?, ?, ?)",
                                (struct.get('id'), site_id, struct.get('name'), struct.get('name2'), struct.get('type'))
                            )
                            structure_count += 1
        count = stream_elements(legends_plus_clean, 'site', import_site_plus)
        conn.commit()
        print(f"  Updated {count} sites, imported {structure_count} structures.")

        # Entities
        print("\nImporting entities...")
        pos_count = assign_count = 0
        def import_entity(data):
            nonlocal pos_count, assign_count
            entity_id = data.get('id')
            cursor.execute(
                "INSERT OR REPLACE INTO entities (id, name, race, type) VALUES (?, ?, ?, ?)",
                (entity_id, data.get('name'), data.get('race'), data.get('type'))
            )

            # Positions
            positions = data.get('entity_position', [])
            if isinstance(positions, dict):
                positions = [positions]
            for pos in positions:
                if isinstance(pos, dict):
                    cursor.execute(
                        "INSERT OR REPLACE INTO entity_positions (entity_id, position_id, name) VALUES (?, ?, ?)",
                        (entity_id, pos.get('id'), pos.get('name'))
                    )
                    pos_count += 1

            # Assignments
            assignments = data.get('entity_position_assignment', [])
            if isinstance(assignments, dict):
                assignments = [assignments]
            for assign in assignments:
                if isinstance(assign, dict):
                    cursor.execute(
                        "INSERT OR REPLACE INTO entity_position_assignments (entity_id, position_id, histfig_id) VALUES (?, ?, ?)",
                        (entity_id, assign.get('position_id'), assign.get('histfig'))
                    )
                    assign_count += 1
        count = stream_elements(legends_plus_clean, 'entity', import_entity)
        conn.commit()
        print(f"  Imported {count} entities, {pos_count} positions, {assign_count} assignments.")

        # Relationships
        print("\nImporting relationships...")
        def import_rel(data):
            cursor.execute(
                "INSERT OR IGNORE INTO hf_relationships (source_hf, target_hf, relationship, year) VALUES (?, ?, ?, ?)",
                (data.get('source_hf'), data.get('target_hf'), data.get('relationship'), data.get('year'))
            )
        count = stream_elements(legends_plus_clean, 'historical_event_relationship', import_rel)
        conn.commit()
        print(f"  Imported {count} relationships.")

        # Update historical events with more detailed data
        print("\nUpdating historical events...")
        # First get existing years from the database
        event_years = {}
        for row in cursor.execute("SELECT id, year FROM historical_events WHERE year IS NOT NULL"):
            event_years[int(row[0])] = int(row[1])
        print(f"  Found years for {len(event_years)} existing events")

        known_fields = {'id', 'year', 'type', 'site_id', 'site', 'hfid', 'civ_id', 'civ',
                       'state', 'reason', 'slayer_hfid', 'slayer_hf', 'death_cause',
                       'artifact_id', 'entity_id', 'structure_id'}
        def import_event_plus(data):
            event_id = data.get('id')
            year = event_years.get(int(event_id)) if event_id is not None else None
            extra = {k: v for k, v in data.items() if k not in known_fields}
            cursor.execute(
                """INSERT OR REPLACE INTO historical_events
                   (id, year, type, site_id, hfid, civ_id, state, reason, slayer_hfid,
                    death_cause, artifact_id, entity_id, structure_id, extra_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, year, data.get('type'),
                 data.get('site_id') or data.get('site'), data.get('hfid'),
                 data.get('civ_id') or data.get('civ'), data.get('state'), data.get('reason'),
                 data.get('slayer_hfid') or data.get('slayer_hf'), data.get('death_cause'),
                 data.get('artifact_id'), data.get('entity_id'), data.get('structure_id'),
                 json.dumps(extra) if extra else None)
            )
        count = stream_elements(legends_plus_clean, 'historical_event', import_event_plus)
        conn.commit()
        print(f"  Updated {count} historical events.")

        # Artifacts
        print("\nUpdating artifacts...")
        debug_shown = False
        def import_artifact_plus(data):
            nonlocal debug_shown
            if not debug_shown:
                print(f"  DEBUG - Sample artifact keys: {list(data.keys())}")
                debug_shown = True
            cursor.execute(
                """UPDATE artifacts SET
                   item_type = COALESCE(?, item_type),
                   item_subtype = COALESCE(?, item_subtype),
                   mat = COALESCE(?, mat),
                   creator_hfid = COALESCE(?, creator_hfid),
                   site_id = COALESCE(?, site_id),
                   holder_hfid = COALESCE(?, holder_hfid)
                   WHERE id = ?""",
                (data.get('item_type'), data.get('item_subtype'), data.get('mat'),
                 data.get('creator_hfid'), data.get('site_id'), data.get('holder_hfid'),
                 data.get('id'))
            )
            # If artifact doesn't exist yet, insert it
            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO artifacts
                       (id, name, item_type, item_subtype, mat, creator_hfid, site_id, holder_hfid)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (data.get('id'), data.get('name'),
                     data.get('item_type'), data.get('item_subtype'), data.get('mat'),
                     data.get('creator_hfid'), data.get('site_id'), data.get('holder_hfid'))
                )
        count = stream_elements(legends_plus_clean, 'artifact', import_artifact_plus)
        conn.commit()
        print(f"  Updated {count} artifacts.")

        # Written content
        print("\nImporting written content...")
        style_count = ref_count = 0
        def import_content(data):
            nonlocal style_count, ref_count
            content_id = data.get('id')
            cursor.execute(
                "INSERT OR REPLACE INTO written_content (id, title, type, author_hfid, page_start, page_end) VALUES (?, ?, ?, ?, ?, ?)",
                (content_id, data.get('title'), data.get('type'), data.get('author'),
                 data.get('page_start'), data.get('page_end'))
            )

            # Styles
            styles = data.get('style', [])
            if isinstance(styles, str):
                styles = [styles]
            for style in styles:
                cursor.execute(
                    "INSERT OR REPLACE INTO written_content_styles (written_content_id, style) VALUES (?, ?)",
                    (content_id, style)
                )
                style_count += 1

            # References
            refs = data.get('reference', [])
            if isinstance(refs, dict):
                refs = [refs]
            for ref in refs:
                if isinstance(ref, dict):
                    cursor.execute(
                        "INSERT OR REPLACE INTO written_content_references (written_content_id, ref_type, ref_id) VALUES (?, ?, ?)",
                        (content_id, ref.get('type'), ref.get('id'))
                    )
                    ref_count += 1
        count = stream_elements(legends_plus_clean, 'written_content', import_content)
        conn.commit()
        print(f"  Imported {count} written content, {style_count} styles, {ref_count} references.")

        conn.close()

        # Update master database
        print("\nUpdating world status...")
        update_world_has_plus(world_id)

        # Also update name and altname in master db
        if name or altname:
            master_conn = init_master_db()
            if name:
                master_conn.execute("UPDATE worlds SET name = ? WHERE id = ? AND (name IS NULL OR name = '' OR name = 'Unknown World')", (name, world_id))
            if altname:
                master_conn.execute("UPDATE worlds SET altname = ? WHERE id = ?", (altname, world_id))
            master_conn.commit()
            master_conn.close()

        print("\n" + "=" * 50)
        print("Merge complete!")
        print(f"World '{world_id}' now has legends_plus data.")
        print("=" * 50)
        return True

    finally:
        # Cleanup temp file
        os.unlink(legends_plus_clean)


if __name__ == '__main__':
    import sys

    # Check for merge mode: --merge <world_id> <db_path> <plus_path>
    if len(sys.argv) > 1 and sys.argv[1] == '--merge':
        if len(sys.argv) < 5:
            print("Usage: build.py --merge <world_id> <db_path> <plus_path>")
            sys.exit(1)
        world_id = sys.argv[2]
        db_path = sys.argv[3]
        plus_path = sys.argv[4]
        success = run_merge_plus(world_id, db_path, plus_path)
        sys.exit(0 if success else 1)

    # Normal import mode
    legends_path = sys.argv[1] if len(sys.argv) > 1 else None
    plus_path = sys.argv[2] if len(sys.argv) > 2 else None

    success = run_import(legends_path, plus_path)
    sys.exit(0 if success else 1)
