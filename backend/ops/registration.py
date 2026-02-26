"""
Registration form ingestion command.
"""

from flask.cli import with_appcontext
from flask import current_app

from .utils import fetch_tally_submissions, ingest_submissions
from ..models import Reg_Data



# Field mapping: model field -> Tally question key
REGISTRATION_FIELD_MAPPING = {
    "Name": "name",
    "Phone": "phone",
    "Stream": "batch",
    "FoodPref": "food_preference",
    "TShirtSize": "tshirt_size",
    "tshirt_preference": "tshirt_preference",
}


def process_registration_record(record):
    """
    Process registration record and prepare for insertion.

    Args:
        record: Dict with extracted field values

    Returns:
        Tuple of (processed_record dict, should_insert bool)
    """

    amount_shirt = current_app.config.get("AMOUNT_SHIRT")
    amount_noshirt = current_app.config.get("AMOUNT_NOSHIRT")

    tshirt_interest = record.get("tshirt_preference") == "Yes"
    payable = amount_shirt if tshirt_interest else amount_noshirt

    processed = {
        "SubID": record["SubID"],
        "SubAt": record["SubAt"],
        "Name": record["Name"],
        "Phone": record["Phone"],
        "Stream": record["Stream"],
        "FoodPref": record["FoodPref"],
        "TShirtInt": tshirt_interest,
        "TShirtSize": record.get("TShirtSize"),
        "PaymentMethod": "CR",
        "PaymentScreenshot": None,
        "Payable": payable,
    }

    return processed, True


def register_registration_command(app):
    """Register the registration ingestion CLI command."""

    @app.cli.command("ingest-registration-data")
    @with_appcontext
    def ingest_api_data():
        """Fetches new registrations from Tally API and saves them to the database."""

        print("[OPS] Running Tally API Registration Data Ingestion Task")

        tally_api_key = current_app.config.get("TALLY_API_KEY")
        tally_form_id = current_app.config.get("TALLY_REGISTRATION_FORM_ID")

        if not all([tally_api_key, tally_form_id]):
            print("❌ FATAL: Tally API registration environment variables are not set.")
            return

        try:
            api_response = fetch_tally_submissions(tally_api_key, tally_form_id)
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch data from Tally API: {e}")
            return

        submissions = api_response.get("submissions", [])
        print(f"Fetched {len(submissions)} submissions from Tally API.")

        try:
            new_records_added = ingest_submissions(
                api_response,
                Reg_Data,
                REGISTRATION_FIELD_MAPPING,
                process_registration_record,
            )

            if new_records_added:
                print("✅ New registration data ingested successfully.")
            else:
                print("No new registration data found.")

        except Exception as e:
            print(f"❌ An error occurred during database insertion: {e}")
            return

        print("[OPS] Registration Data Ingestion Task Finished")
