-- DF Tales SQLite Schema

-- World info
CREATE TABLE IF NOT EXISTS world (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    altname TEXT
);

-- Creature definitions (from creature_raw in legends_plus.xml)
CREATE TABLE IF NOT EXISTS creatures (
    creature_id TEXT PRIMARY KEY,
    name_singular TEXT,
    name_plural TEXT
);

-- Geographic regions
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    coords TEXT,
    evilness TEXT
);

-- Underground regions
CREATE TABLE IF NOT EXISTS underground_regions (
    id INTEGER PRIMARY KEY,
    type TEXT,
    depth INTEGER
);

-- Landmasses (continents/islands)
CREATE TABLE IF NOT EXISTS landmasses (
    id INTEGER PRIMARY KEY,
    name TEXT,
    coord_1 TEXT,
    coord_2 TEXT
);

-- Mountain peaks
CREATE TABLE IF NOT EXISTS mountain_peaks (
    id INTEGER PRIMARY KEY,
    name TEXT,
    coords TEXT,
    height INTEGER,
    is_volcano INTEGER DEFAULT 0
);

-- Sites (locations)
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    coords TEXT,
    rectangle TEXT,
    civ_id INTEGER,
    cur_owner_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sites_type ON sites(type);
CREATE INDEX IF NOT EXISTS idx_sites_civ ON sites(civ_id);

-- Structures within sites
CREATE TABLE IF NOT EXISTS structures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    local_id INTEGER,
    site_id INTEGER,
    name TEXT,
    name2 TEXT,
    type TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_structures_site ON structures(site_id);

-- Site properties
CREATE TABLE IF NOT EXISTS site_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    property_id INTEGER,
    type TEXT,
    owner_hfid INTEGER,
    structure_local_id INTEGER,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_site_properties_site ON site_properties(site_id);

-- Entities (civilizations, governments)
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT,
    race TEXT,
    type TEXT
);
CREATE INDEX IF NOT EXISTS idx_entities_race ON entities(race);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);

-- Entity positions
CREATE TABLE IF NOT EXISTS entity_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    position_id INTEGER,
    name TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_entity_positions_entity ON entity_positions(entity_id);

-- Entity position assignments
CREATE TABLE IF NOT EXISTS entity_position_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    position_id INTEGER,
    histfig_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_epa_entity ON entity_position_assignments(entity_id);
CREATE INDEX IF NOT EXISTS idx_epa_histfig ON entity_position_assignments(histfig_id);

-- Historical figures
CREATE TABLE IF NOT EXISTS historical_figures (
    id INTEGER PRIMARY KEY,
    name TEXT,
    race TEXT,
    caste TEXT,
    sex INTEGER,
    birth_year INTEGER,
    death_year INTEGER
);
CREATE INDEX IF NOT EXISTS idx_hf_race ON historical_figures(race);
CREATE INDEX IF NOT EXISTS idx_hf_name ON historical_figures(name);

-- Historical figure entity links
CREATE TABLE IF NOT EXISTS hf_entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hfid INTEGER,
    entity_id INTEGER,
    link_type TEXT,
    link_strength INTEGER,
    FOREIGN KEY (hfid) REFERENCES historical_figures(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_hf_entity_links_hfid ON hf_entity_links(hfid);
CREATE INDEX IF NOT EXISTS idx_hf_entity_links_entity ON hf_entity_links(entity_id);

-- Historical figure site links
CREATE TABLE IF NOT EXISTS hf_site_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hfid INTEGER,
    site_id INTEGER,
    link_type TEXT,
    FOREIGN KEY (hfid) REFERENCES historical_figures(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_hf_site_links_hfid ON hf_site_links(hfid);
CREATE INDEX IF NOT EXISTS idx_hf_site_links_site ON hf_site_links(site_id);

-- Historical figure relationships
CREATE TABLE IF NOT EXISTS hf_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_hf INTEGER,
    target_hf INTEGER,
    relationship TEXT,
    year INTEGER,
    UNIQUE(source_hf, target_hf, relationship, year)
);
CREATE INDEX IF NOT EXISTS idx_hf_rel_source ON hf_relationships(source_hf);
CREATE INDEX IF NOT EXISTS idx_hf_rel_target ON hf_relationships(target_hf);

-- Artifacts
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY,
    name TEXT,
    item_type TEXT,
    item_subtype TEXT,
    mat TEXT,
    creator_hfid INTEGER,
    site_id INTEGER,
    holder_hfid INTEGER
);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(item_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_creator ON artifacts(creator_hfid);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name COLLATE NOCASE);

-- Historical events (polymorphic)
CREATE TABLE IF NOT EXISTS historical_events (
    id INTEGER PRIMARY KEY,
    year INTEGER,
    type TEXT,
    site_id INTEGER,
    hfid INTEGER,
    civ_id INTEGER,
    state TEXT,
    reason TEXT,
    slayer_hfid INTEGER,
    death_cause TEXT,
    artifact_id INTEGER,
    entity_id INTEGER,
    structure_id INTEGER,
    extra_data TEXT  -- JSON string
);
CREATE INDEX IF NOT EXISTS idx_events_year ON historical_events(year);
CREATE INDEX IF NOT EXISTS idx_events_type ON historical_events(type);
CREATE INDEX IF NOT EXISTS idx_events_site ON historical_events(site_id);
CREATE INDEX IF NOT EXISTS idx_events_hfid ON historical_events(hfid);

-- Written content
CREATE TABLE IF NOT EXISTS written_content (
    id INTEGER PRIMARY KEY,
    title TEXT,
    type TEXT,
    author_hfid INTEGER,
    page_start INTEGER,
    page_end INTEGER
);
CREATE INDEX IF NOT EXISTS idx_wc_type ON written_content(type);
CREATE INDEX IF NOT EXISTS idx_wc_author ON written_content(author_hfid);
CREATE INDEX IF NOT EXISTS idx_wc_title ON written_content(title COLLATE NOCASE);

-- Written content styles
CREATE TABLE IF NOT EXISTS written_content_styles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    written_content_id INTEGER,
    style TEXT,
    FOREIGN KEY (written_content_id) REFERENCES written_content(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_wcs_content ON written_content_styles(written_content_id);

-- Written content references
CREATE TABLE IF NOT EXISTS written_content_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    written_content_id INTEGER,
    ref_type TEXT,
    ref_id INTEGER,
    FOREIGN KEY (written_content_id) REFERENCES written_content(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_wcr_content ON written_content_references(written_content_id);

-- Rivers
CREATE TABLE IF NOT EXISTS rivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    path TEXT,
    end_pos TEXT
);

-- World constructions (roads, bridges, tunnels)
CREATE TABLE IF NOT EXISTS world_constructions (
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    coords TEXT
);
CREATE INDEX IF NOT EXISTS idx_wc_type ON world_constructions(type);
