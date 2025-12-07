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
from pathlib import Path
from lxml import etree

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "world.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# XML files (user should place these in the base directory)
LEGENDS_FILE = None
LEGENDS_PLUS_FILE = None


def find_xml_files():
    """Find legends XML files in the base directory."""
    global LEGENDS_FILE, LEGENDS_PLUS_FILE

    for f in BASE_DIR.glob("*.xml"):
        name = f.name.lower()
        if "legends_plus" in name:
            LEGENDS_PLUS_FILE = f
        elif "legends" in name:
            LEGENDS_FILE = f

    return LEGENDS_FILE is not None and LEGENDS_PLUS_FILE is not None


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
    """Extract world name and altname from legends_plus XML."""
    name = altname = None

    context = etree.iterparse(filepath, events=('end',), tag=('name', 'altname'))
    for event, elem in context:
        if elem.tag == 'name' and name is None:
            name = elem.text
        elif elem.tag == 'altname':
            altname = elem.text
            break
        elem.clear()

    del context
    return name, altname


def init_db():
    """Initialize database with schema."""
    DATA_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Read and execute schema
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    return conn


def clear_tables(conn):
    """Clear all tables for fresh import."""
    print("\nClearing existing data...")

    tables = [
        'world', 'regions', 'underground_regions', 'landmasses', 'mountain_peaks',
        'sites', 'structures', 'site_properties', 'entities', 'entity_positions',
        'entity_position_assignments', 'historical_figures', 'hf_entity_links',
        'hf_site_links', 'hf_relationships', 'artifacts', 'historical_events',
        'written_content', 'written_content_styles', 'written_content_references'
    ]

    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def run_import():
    """Main import function."""
    print("=" * 50)
    print("DF-World XML Import")
    print("=" * 50)

    # Find XML files
    if not find_xml_files():
        print("\nERROR: Could not find XML files!")
        print("Please place your legends XML files in:", BASE_DIR)
        print("Expected: *legends.xml and *legends_plus.xml")
        return False

    print(f"\nFound XML files:")
    print(f"  Legends: {LEGENDS_FILE.name}")
    print(f"  Legends+: {LEGENDS_PLUS_FILE.name}")

    # Sanitize XML files
    print("\nSanitizing XML files...")
    legends_clean = sanitize_xml_file(LEGENDS_FILE)
    legends_plus_clean = sanitize_xml_file(LEGENDS_PLUS_FILE)

    try:
        # Initialize database
        print("\nInitializing database...")
        conn = init_db()
        clear_tables(conn)
        cursor = conn.cursor()

        # Import world info
        print("\nImporting world info...")
        name, altname = get_world_info(legends_plus_clean)
        cursor.execute("INSERT INTO world (name, altname) VALUES (?, ?)", (name, altname))
        print(f"  World: {name} ({altname})")
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
                "INSERT OR REPLACE INTO artifacts (id, name, item_type, item_subtype, mat) VALUES (?, ?, ?, ?, ?)",
                (data.get('id'), data.get('name') or data.get('name_string'),
                 data.get('item_type'), data.get('item_subtype'), data.get('mat'))
            )
        count = stream_elements(legends_clean, 'artifact', import_artifact)
        conn.commit()
        print(f"  Imported {count} artifacts.")

        # === LEGENDS_PLUS.XML ===
        print("\n--- Processing legends_plus.xml ---")

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

        # Relationships
        print("\nImporting relationships...")
        def import_rel(data):
            cursor.execute(
                "INSERT INTO hf_relationships (source_hf, target_hf, relationship, year) VALUES (?, ?, ?, ?)",
                (data.get('source_hf'), data.get('target_hf'), data.get('relationship'), data.get('year'))
            )
        count = stream_elements(legends_plus_clean, 'historical_event_relationship', import_rel)
        conn.commit()
        print(f"  Imported {count} relationships.")

        # Historical events
        print("\nImporting historical events...")
        known_fields = {'id', 'year', 'type', 'site_id', 'site', 'hfid', 'civ_id', 'civ',
                       'state', 'reason', 'slayer_hfid', 'slayer_hf', 'death_cause',
                       'artifact_id', 'entity_id', 'structure_id'}
        def import_event(data):
            extra = {k: v for k, v in data.items() if k not in known_fields}
            cursor.execute(
                """INSERT INTO historical_events
                   (id, year, type, site_id, hfid, civ_id, state, reason, slayer_hfid,
                    death_cause, artifact_id, entity_id, structure_id, extra_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data.get('id'), data.get('year'), data.get('type'),
                 data.get('site_id') or data.get('site'), data.get('hfid'),
                 data.get('civ_id') or data.get('civ'), data.get('state'), data.get('reason'),
                 data.get('slayer_hfid') or data.get('slayer_hf'), data.get('death_cause'),
                 data.get('artifact_id'), data.get('entity_id'), data.get('structure_id'),
                 json.dumps(extra) if extra else None)
            )
        count = stream_elements(legends_plus_clean, 'historical_event', import_event)
        conn.commit()
        print(f"  Imported {count} historical events.")

        # Written content
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
        print("\n" + "=" * 50)
        print("Import complete!")
        print("=" * 50)
        return True

    finally:
        # Cleanup temp files
        os.unlink(legends_clean)
        os.unlink(legends_plus_clean)


if __name__ == '__main__':
    run_import()
