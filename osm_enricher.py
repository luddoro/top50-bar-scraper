import argparse
import json
import os
import time
from pathlib import Path

import requests


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

OSM_API_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.getenv("OSM_USER_AGENT", "bars-scraper/1.0")


def build_query(bar):
    """Create a search query from the bar name and location."""
    if bar.get("location"):
        return f"{bar['name']}, {bar['location']}"
    return bar.get("name", "")


def enrich_bar(bar, timeout=20, max_retries=3):
    """Send a single OpenStreetMap lookup request for one bar."""
    query = build_query(bar)
    if not query:
        return {
            **bar,
            "openstreetmap": {
                "status": "missing_query",
                "query": query,
            },
        }

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
        "extratags": 1,
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(OSM_API_URL, params=params, headers=headers, timeout=timeout)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
                if attempt < max_retries - 1:
                    time.sleep(wait_seconds)
                    continue
                raise requests.HTTPError("OpenStreetMap rate limit exceeded")

            response.raise_for_status()
            data = response.json()
            break
        except requests.RequestException as exc:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return {
                **bar,
                "openstreetmap": {
                    "status": "request_error",
                    "query": query,
                    "error": str(exc),
                },
            }

    if not data:
        return {
            **bar,
            "openstreetmap": {
                "status": "not_found",
                "query": query,
            },
        }

    place = data[0]

    return {
        **bar,
        "openstreetmap": {
            "status": "ok",
            "query": query,
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "display_name": place.get("display_name"),
            "address": place.get("address"),
            "latitude": place.get("lat"),
            "longitude": place.get("lon"),
            "category": place.get("type"),
            "importance": place.get("importance"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Enrich bars with OpenStreetMap data")
    parser.add_argument("--input", default="50_best_bars_highest_rank.json", help="Path to the input JSON file")
    parser.add_argument("--output", default="50_best_bars_with_osm.json", help="Path to write the enriched JSON file")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--rate-per-minute", type=int, default=4, help="Maximum requests per minute to Nominatim (default 4)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as handle:
        bars = json.load(handle)

    interval = 60.0 / float(args.rate_per_minute) if args.rate_per_minute > 0 else 15.0
    last_call = 0.0

    enriched_bars = []
    for index, bar in enumerate(bars, start=1):
        # Skip if we already have OSM data present
        existing = bar.get("openstreetmap")
        if existing and existing.get("status") == "ok":
            print(f"[{index}/{len(bars)}] Skipping '{bar.get('name')}' — already has OpenStreetMap data")
            enriched_bars.append(bar)
            continue

        # rate limit: ensure interval between requests
        elapsed = time.time() - last_call
        if elapsed < interval:
            to_wait = interval - elapsed
            print(f"Waiting {to_wait:.1f}s to respect rate limit before querying '{bar.get('name')}'")
            time.sleep(to_wait)

        print(f"[{index}/{len(bars)}] Querying OpenStreetMap for: {bar.get('name')}")
        result = enrich_bar(bar, timeout=args.timeout)
        last_call = time.time()

        osm = result.get("openstreetmap", {})
        status = osm.get("status")
        if status == "request_error":
            # wait 60s and retry once
            print(f"Request error for '{bar.get('name')}', waiting 60s and retrying once...")
            time.sleep(60)
            # respect rate limit again
            elapsed = time.time() - last_call
            if elapsed < interval:
                time.sleep(interval - elapsed)
            result = enrich_bar(bar, timeout=args.timeout)
            last_call = time.time()

        enriched_bars.append(result)

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(enriched_bars, handle, indent=4, ensure_ascii=False)

    print(f"Saved {len(enriched_bars)} enriched entries to {output_path}")


if __name__ == "__main__":
    main()
