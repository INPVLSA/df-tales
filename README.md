# DF-World

A web interface for exploring your Dwarf Fortress world history.

## Features

- **Historical Figures** — Browse all characters from your world, filter by race, search by name
- **Sites** — Explore fortresses, towns, caves, and other locations
- **Events** — View the history of your world year by year
- **Dashboard** — See world statistics at a glance

## Getting Started

### 1. Export Your World Data (requires DFHack)

In Dwarf Fortress with [DFHack](https://dfhack.org/):
1. Enter Legends mode
2. Run `exportlegends info` in the DFHack console

This creates both required XML files (`*-legends.xml` and `*-legends_plus.xml`).

### 2. Install & Run

```bash
git clone git@github.com:INPVLSA/df-world.git
cd df-world
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Import Your World

Copy both XML files to the `df-world` folder, then:

```bash
python build.py
```

### 4. Start Exploring

```bash
python app.py
```

Open http://localhost:5001 in your browser.

## Custom Race Icons

Add PNG icons to `static/icons/races/` named by race code (e.g., `DWARF.png`). Falls back to ASCII symbols.

## License

[MIT](LICENSE)
