# Worlds 50 Best Bars Scraper

This project scrapes the Worlds 50 Best Bars listings and saves the highest-ranked bars to a JSON file.

## Requirements
- Python 3.12+
- A virtual environment

### 1. Create and activate a virtual environment
On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r .requirements-txt
```

### 3. Create a .env file
Create a file named `.env` in the project root with values such as:

```env
OUTPUT_FILE=50_best_bars_highest_rank.json
REQUEST_TIMEOUT=10
```

You can copy the example file instead:

```bash
cp .env.example .env
```

### 4. Run the scraper

```bash
python top50scraper.py
```

The script will write the results to the file specified by `OUTPUT_FILE` (default: `50_best_bars_highest_rank.json`).

## Output
The generated JSON contains each bar's name, location, highest rank, year, and source URL.

## Enrich with OpenStreetMap
You can also enrich the scraped data with OpenStreetMap details such as latitude/longitude, a display address, and place metadata.

### 1. Optional: set a custom user agent
If you want, you can add a custom user-agent to your `.env` file:

```env
OSM_USER_AGENT=your-app-name/1.0
```

### 2. Run the enrichment script

```bash
python osm_enricher.py
```

Notes:
- The enricher uses the Nominatim (OpenStreetMap) API and enforces a default rate limit of 4 requests per minute to avoid being rate-limited. You can change this with `--rate-per-minute`.
- Requests are performed sequentially (no concurrency) and the script will skip bars that already contain `openstreetmap` data in the input JSON.

This will read the scraped data from `50_best_bars_highest_rank.json` and write the enriched output to `50_best_bars_with_osm.json`.
