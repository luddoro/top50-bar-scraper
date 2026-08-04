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
