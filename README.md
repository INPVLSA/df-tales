![fig.png](docs/fig.png)

A web interface for exploring your Dwarf Fortress world history.

## Features

- **Historical Figures** — Browse all characters, filter by race, search by name, view affiliations and site links
- **Sites** — Explore fortresses, towns, caves, and other locations with their structures
- **Artifacts** — Discover named items with their creators, materials, and current holders
- **Events** — View the history of your world year by year
- **Interactive References** — Click on any figure, site, artifact, or entity name to open a detailed popup with nested navigation
- **Dashboard** — See world statistics at a glance, manage multiple worlds

## Getting Started

### 1. Export Your World Data

**Option A: With DFHack (recommended)**
In Dwarf Fortress with [DFHack](https://dfhack.org/):
1. Enter Legends mode (see below)
2. Press the export button (DFHack adds this automatically)

This creates `*-legends.xml` and `*-legends_plus.xml` with full data.

**Option B: Vanilla DF**
In Legends mode, export your world data to get `*-legends.xml`.

Note: Without DFHack, some features are limited (no structures, entities, relationships, artifact details, or written content).

#### How to Access Legends Mode

**Classic DF:** Main Menu → Legends

**Steam DF:**
1. Save and exit your current game
2. Main Menu → **Start Playing** → Select your world
3. Choose **Legends** mode instead of Continue/Fortress/Adventure

**If Legends doesn't appear:** Your world needs generated history. Create a new world or let your current game run for a while.

### 2. Install & Run

```bash
git clone git@github.com:INPVLSA/df-world.git
cd df-world
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Import Your World

Start the server and use the web interface to upload your XML files:

```bash
python app.py
```

Open http://localhost:5001 and drag & drop your XML files to import.

You can also import via command line:

```bash
python build.py legends.xml [legends_plus.xml]
```

## Support

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/inpvlsa)

## License

[MIT](LICENSE)

![fig-mod.png](docs/fig-mod.png)
![fig.png](docs/fig.png)
![sit-mod.png](docs/sit-mod.png)
![db.png](docs/db.png)
![sit.png](docs/sit.png)
![art.png](docs/art.png)
