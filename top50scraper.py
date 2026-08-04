import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures
import re


def load_env_file():
    """Load values from a local .env file if present."""
    env_path = Path(".env")
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

OUTPUT_FILE = os.getenv("OUTPUT_FILE", "50_best_bars_highest_rank.json")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# 1. Define all the URLs you want to scrape
urls_to_scrape = [
    "https://www.theworlds50best.com/bars/best-in-the-world/list/1-50",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2009",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2010",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2011",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2012",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2013",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2014",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2015",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2016",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2017",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2018",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2019",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2020",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2021",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2022",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2023",
    "https://www.theworlds50best.com/bars/best-in-the-world/previous-list/2024",
    "https://www.theworlds50best.com/bars/best-in-europe/list/1-50",
    "https://www.theworlds50best.com/bars/best-in-asia/list/1-50"

]


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_and_parse(url):
    """Fetches and parses a single URL."""
    print(f"Requesting: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return []
    except requests.RequestException:
        return []
        
    soup = BeautifulSoup(response.text, 'html.parser')
    list_items = soup.find_all(class_="list-item")
    
    extracted_bars = []
    for item in list_items:
        item_top = item.find(class_="item-top")
        rank = item_top.get_text(strip=True) if item_top else None
            
        item_bottom = item.find(class_="item-bottom")
        name, location = None, None
        
        if item_bottom:
            bottom_text = item_bottom.get_text(separator="\n", strip=True).split("\n")
            name = bottom_text[0] if len(bottom_text) >= 1 else None
            location = bottom_text[1] if len(bottom_text) >= 2 else None
            
        if not name:
            continue
            
        extracted_bars.append({
            "name": name,
            "location": location,
            "rank": rank,
            "source_url": url
        })
        
    return extracted_bars

def extract_year_from_url(url):
    """Extracts the 4-digit year from the URL, or defaults to 'Latest'."""
    match = re.search(r'/(\d{4})/', url)
    return match.group(1) if match else "Latest"

# 2. CONCURRENCY: Fetch all URLs simultaneously
all_extracted_bars = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(fetch_and_parse, urls_to_scrape)
    for result_list in results:
        all_extracted_bars.extend(result_list)

# 3. Deduplicate and ONLY keep the highest rank
unique_bars_dict = {}

for bar in all_extracted_bars:
    name = bar.get("name")
    location = bar.get("location")
    rank_str = bar.get("rank")
    url = bar.get("source_url")
    
    if not name or not rank_str:
        continue
        
    try:
        # Strip any accidental letters/symbols and convert to an integer
        current_rank = int(re.sub(r'\D', '', rank_str))
    except ValueError:
        continue # Skip if rank is completely unreadable
        
    year = extract_year_from_url(url)
    
    # If it's a new bar, add it to our dictionary
    if name not in unique_bars_dict:
        entry = {
            "name": name,
            "highest_rank": current_rank,
            "year": year,
            "source_url": url
        }
        if location:  # Only add location if it exists to prevent nulls
            entry["location"] = location
            
        unique_bars_dict[name] = entry
        
    # If the bar already exists, check if this new rank is better (a lower number)
    else:
        if current_rank < unique_bars_dict[name]["highest_rank"]:
            # Overwrite with the better rank data
            unique_bars_dict[name]["highest_rank"] = current_rank
            unique_bars_dict[name]["year"] = year
            unique_bars_dict[name]["source_url"] = url

# 4. Export to JSON
final_bars_list = list(unique_bars_dict.values())

# Sort the final list by their highest rank so the JSON is ordered beautifully (1 to 50+)
final_bars_list = sorted(final_bars_list, key=lambda x: x["highest_rank"])

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_bars_list, f, indent=4, ensure_ascii=False)

print(f"Scraping complete! Found {len(final_bars_list)} unique bars.")