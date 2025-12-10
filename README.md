<p align="center">
  <img alt="DF Tales Icon" height="50" src="static/ico.png"/>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img alt="DF Tales" height="50" src="docs/title.png"/>
</p>

<p align="center">A web interface for exploring your Dwarf Fortress world history.</p>


![fig.png](docs/fig.png)


## Features

- **Historical Figures** — Browse all characters, filter by race, search by name, view affiliations and site links
- **Sites** — Explore fortresses, towns, caves, and other locations with their structures
- **Artifacts** — Discover named items with their creators, materials, and current holders
- **Events** — View the history of your world year by year
- **Interactive Map** — Terrain map with biomes, evilness variants, and mountain heights based on peak data. Pan, zoom (toward cursor), and click sites/peaks to navigate
- **Family Tree** — Visualize genealogical relationships with parents, grandparents, spouses, siblings, children, and grandchildren
- **Interactive References** — Click on any figure, site, artifact, or entity name to open a detailed popup with nested navigation
- **Dashboard** — See world statistics at a glance, manage multiple worlds

## Getting Started

### 1. Export Your World Data

#### With DFHack (Recommended)

[DFHack](https://dfhack.org/) provides extended data including structures, entities, relationships, and artifact details.

**From a new world or after world generation:**
1. Main Menu → **Legends** → Select your world
2. Click **Export XML** (DFHack adds a toggle for extended data - enable it)
3. Both `*-legends.xml` and `*-legends_plus.xml` are created

**From an active fortress/adventure game:**

⚠️ **Warning:** This is a ONE WAY TRIP - save your game first!

1. **Save your game** (you cannot safely return to fort/adventure mode)
2. Open DFHack console (press `` ` ``)
3. Run: `open-legends`
4. Confirm the save reminder dialog
5. Click **Export XML** with DFHack toggle enabled

See [DFHack exportlegends documentation](https://docs.dfhack.org/en/stable/docs/tools/exportlegends.html) for more options.

#### Without DFHack (Vanilla)

1. Main Menu → **Legends** → Select your world
2. Click **Export XML**

Note: Without DFHack, some features are limited (no structures, entities, relationships, artifact details, or written content).

### 2. Install & Run

```bash
git clone git@github.com:INPVLSA/df-world.git
cd df-world
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5001

> **Note:** Use `python3` instead of `python` on systems where Python 2 is the default.

### 3. Import Your World

Drag & drop your XML files into the web interface, or import via command line:

```bash
python build.py legends.xml [legends_plus.xml]
```

## Support

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/inpvlsa)

## License

[MIT](LICENSE)

## Screenshots

<table>
  <tr>
    <td><img src="docs/fig.png" width="400"></td>
    <td><img src="docs/fig-mod.png" width="400"></td>
  </tr>
  <tr>
    <td><img src="docs/sit.png" width="400"></td>
    <td><img src="docs/sit-mod.png" width="400"></td>
  </tr>
  <tr>
    <td><img src="docs/map.png" width="400"></td>
    <td><img src="docs/art.png" width="400"></td>
  </tr>
  <tr>
    <td><img src="docs/graph.png" width="400"></td>
    <td><img src="docs/db.png" width="400"></td>
  </tr>
</table>
