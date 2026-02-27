import os
import sys
import shutil
import requests
import argparse
import logging
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

# === Configuration & Path Setup ===

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "public"
ASSETS_DIR = PROJECT_ROOT / "profile_assets"
TEMPLATE_DIR = PROJECT_ROOT / "scripts" / "templates"
TEMPLATE_FILE = "profile_template.html"
PROFILE_PAGES_DIR = OUTPUT_DIR / "p"

# === Helper Functions ===

def setup_output_dir():
    """Clears and recreates the output directories."""

    logging.info(f"Preparing output directory: {OUTPUT_DIR}")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROFILE_PAGES_DIR, exist_ok=True)


def copy_static_assets():
    """Copies all static assets to the output directory."""

    logging.info(f"Copying static assets from {ASSETS_DIR}...")
    if not ASSETS_DIR.exists():
        logging.warning(
            "profile_assets/ directory not found. No static assets will be copied."
        )
        return
    shutil.copytree(ASSETS_DIR, OUTPUT_DIR, dirs_exist_ok=True)


def get_dummy_data():
    """Returns a hardcoded dictionary of test data."""

    logging.info("Using dummy data for testing.")
    return {
        "data": [
            {
                "id": "TEST1",
                "name": "Test Person 1",
                "paid": 1100,
                "payable": 1100,
                "batch": "B.Tech 3rd",
                "food": "Non Veg",
                "items_rec": "T-SHIRT",
                "tshirt": "Size : XL",
            },
            {
                "id": "TEST2",
                "name": "Test Person 2",
                "paid": 900,
                "payable": 1100,
                "batch": "MCA 1st",
                "food": "Veg",
                "items_rec": "None",
                "tshirt": "Size : M",
            },
        ]
    }


def fetch_data_from_api():
    """Fetches profile data from the production API."""

    api_url = os.environ.get("API_URL")
    api_password = os.environ.get("API_PASSWORD")

    if not api_url or not api_password:
        logging.error("API_URL or API_PASSWORD environment variables are not set. Aborting.")
        sys.exit(1)

    logging.info(f"Fetching data from API: {api_url}")
    try:
        response = requests.post(api_url, json={"password": api_password}, timeout=15)
        response.raise_for_status()  # Raise an exception for bad status codes

        api_data = response.json()
        if "data" not in api_data or not isinstance(api_data["data"], list):
            logging.error("Invalid API response format. Missing 'data' list.")
            sys.exit(1)

        logging.info(f"Successfully fetched {len(api_data['data'])} profiles from API.")
        return api_data
        
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        sys.exit(1)


# === Main Execution ===


def main():
    
    parser = argparse.ArgumentParser(
        description="Builds static profile pages for the Voyage festival app."
    )
    parser.add_argument(
        "--dummy",
        action="store_true",
        help="Use local dummy data instead of fetching from the API.",
    )
    args = parser.parse_args()

    setup_output_dir()
    copy_static_assets()

    if args.dummy:
        profile_data = get_dummy_data()
    else:
        profile_data = fetch_data_from_api()

    if not profile_data or not profile_data.get("data"):
        logging.warning("No profile data found. Exiting without generating pages.")
        return

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_FILE)

    logging.info(f"Generating {len(profile_data['data'])} HTML pages...")
    
    for item in profile_data["data"]:
        rendered_html = template.render(data=item)
        file_path = PROFILE_PAGES_DIR / f"{item['id']}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

    logging.info("🎉 Page generation complete!")


if __name__ == "__main__":
    main()
