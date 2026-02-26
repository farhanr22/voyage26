"""
CR payments form ingestion command.
"""

from flask.cli import with_appcontext
from flask import current_app

from .utils import fetch_tally_submissions, ingest_submissions
from ..models import CR_Payments


# Field mapping: model field -> Tally question key
CR_FIELD_MAPPING = {
    "CRID": "cr-id",
    "Name": "name",
    "Phone": "phone",
    "Amount": "amount",
}


def process_cr_record(record):
    """
    Process CR payment record and prepare for insertion.

    Args:
        record: Dict with extracted field values

    Returns:
        Tuple of (processed_record dict, should_insert bool)
    """

    processed = {
        "SubID": record["SubID"],
        "SubAt": record["SubAt"],
        "CRID": record["CRID"],
        "Name": record["Name"],
        "Phone": record["Phone"],
        "Amount": int(record["Amount"]) if record["Amount"] else 0,
        "Status": "Pending",
    }

    return processed, True


def register_cr_command(app):
    """Register the CR payments ingestion CLI command."""

    @app.cli.command("ingest-cr-data")
    @with_appcontext
    def ingest_cr_data():
        """Fetches new CR payments from Tally API and saves them to the database."""

        print("[OPS] Running Tally API CR Data Ingestion Task")

        tally_api_key = current_app.config.get("TALLY_API_KEY")
        tally_form_id = current_app.config.get("TALLY_CR_FORM_ID")

        if not all([tally_api_key, tally_form_id]):
            print("❌ FATAL: Tally API CR environment variables are not set.")
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
                CR_Payments,
                CR_FIELD_MAPPING,
                process_cr_record,
            )

            if new_records_added:
                print("✅ New CR data ingested successfully.")
            else:
                print("No new CR data found.")

        except Exception as e:
            print(f"❌ An error occurred during database insertion: {e}")
            return

        print("[OPS] CR Data Ingestion Task Finished")
