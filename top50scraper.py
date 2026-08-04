import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
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
BAR_IMAGES_DIR = Path("bar-images")
BAR_IMAGES_DIR.mkdir(exist_ok=True)

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

def slugify(value):
    """Create a filesystem-safe slug from a string."""
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value or "bar").strip("-").lower()
    return value or "bar"


def build_image_filename(bar_name, image_url):
    """Create a bar-name-based filename for an image."""
    parsed = urlparse(image_url or "")
    extension = Path(parsed.path).suffix.lower() or ".jpg"
    return f"{slugify(bar_name)}{extension}"


def download_image(image_url, bar_name):
    """Download an image into the local bar-images directory, reusing existing files."""
    if not image_url:
        return None

    filename = build_image_filename(bar_name, image_url)
    output_path = BAR_IMAGES_DIR / filename
    if output_path.exists():
        return str(output_path)

    try:
        response = requests.get(image_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return None

    output_path.write_bytes(response.content)
    return str(output_path)


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

        item_img_container = item.find(class_="item-img-container")
        image_url = None
        href = None
        if item_img_container:
            href = item_img_container.get("href")
            img_tag = item_img_container.find("img")
            if img_tag:
                image_url = img_tag.get("data-src") or img_tag.get("src")

        if image_url:
            image_url = urljoin(url, image_url)

        listing_url = None
        for anchor in item.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue
            classes = anchor.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            if "item-img-container" in classes:
                listing_url = urljoin(url, href)
                break
            if anchor.get("id") == "contentLink_1635826":
                listing_url = urljoin(url, href)
                break
            if href and "/the-list/" in href and href.endswith(".html"):
                listing_url = urljoin(url, href)
                break
            
        item_bottom = item.find(class_="item-bottom")
        name, location = None, None
        
        if item_bottom:
            bottom_text = item_bottom.get_text(separator="\n", strip=True).split("\n")
            name = bottom_text[0] if len(bottom_text) >= 1 else None
            location = bottom_text[1] if len(bottom_text) >= 2 else None
            
        if not name:
            continue

        image_path = download_image(image_url, name) if image_url else None
            
        extracted_bars.append({
            "name": name,
            "location": location,
            "rank": rank,
            "source_url": url,
            "image_path": image_path,
            "listing_url": listing_url,
        })
        
    return extracted_bars

def extract_year_from_url(url):
    """Extracts the 4-digit year from the URL, or defaults to the current year."""
    match = re.search(r'/((?:19|20)\d{2})(?:/|$)', url)
    return match.group(1) if match else str(datetime.now().year)

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

        if bar.get("image_path"):
            entry["image_path"] = bar["image_path"]
        if bar.get("listing_url"):
            entry["listing_url"] = bar["listing_url"]
            
        unique_bars_dict[name] = entry
        
    # If the bar already exists, update if this new rank is better (a lower number)
    # or if the new information carries a more specific year for the same rank.
    else:
        existing_entry = unique_bars_dict[name]
        if current_rank < existing_entry["highest_rank"]:
            # Overwrite with the better rank data
            existing_entry["highest_rank"] = current_rank
            existing_entry["year"] = year
            existing_entry["source_url"] = url
            if bar.get("image_path"):
                existing_entry["image_path"] = bar["image_path"]
            if bar.get("listing_url"):
                existing_entry["listing_url"] = bar["listing_url"]
        elif current_rank == existing_entry["highest_rank"] and year != existing_entry["year"]:
            existing_entry["year"] = year
            existing_entry["source_url"] = url
            if bar.get("image_path") and not existing_entry.get("image_path"):
                existing_entry["image_path"] = bar["image_path"]
            if bar.get("listing_url") and not existing_entry.get("listing_url"):
                existing_entry["listing_url"] = bar["listing_url"]

# 4. Export to JSON
final_bars_list = list(unique_bars_dict.values())

# Sort the final list by their highest rank so the JSON is ordered beautifully (1 to 50+)
final_bars_list = sorted(final_bars_list, key=lambda x: x["highest_rank"])

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_bars_list, f, indent=4, ensure_ascii=False)

print(f"Scraping complete! Found {len(final_bars_list)} unique bars.")