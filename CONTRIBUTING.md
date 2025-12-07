# Contributing

## Requirements

- Python 3.10+
- Flask 3.0+
- lxml 5.0+

## Database Schema

| Table | Description |
|-------|-------------|
| `world` | World name and alternate name |
| `regions` | Geographic regions |
| `underground_regions` | Cavern layers |
| `landmasses` | Continents and islands |
| `mountain_peaks` | Mountains and volcanoes |
| `sites` | Locations (fortresses, towns, caves) |
| `structures` | Buildings within sites |
| `site_properties` | Site ownership and properties |
| `entities` | Civilizations and organizations |
| `entity_positions` | Government positions |
| `entity_position_assignments` | Who holds which position |
| `historical_figures` | Characters with race, birth/death years |
| `hf_entity_links` | Figure-to-entity relationships |
| `hf_site_links` | Figure-to-site relationships |
| `hf_relationships` | Figure-to-figure relationships |
| `artifacts` | Named items |
| `historical_events` | Events with type, year, participants |
| `written_content` | Books and written works |
| `written_content_styles` | Writing styles |
| `written_content_references` | References in written works |

## Import Process

The `build.py` script:

1. Finds `*legends.xml` and `*legends_plus.xml` in the project root
2. Sanitizes XML (converts CP437 encoding, removes invalid characters)
3. Streams and parses XML using `lxml.etree.iterparse` for memory efficiency
4. Populates SQLite database using the schema in `schema.sql`

## Race Icons

Race icons are matched by the race code (e.g., `DWARF`, `HUMAN`, `GOBLIN`). The app checks `static/icons/races/{RACE_CODE}.png` and falls back to ASCII symbols defined in `RACE_DATA` and `RACE_PATTERNS` in `app.py`.
