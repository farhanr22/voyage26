import base64
import json
import requests
from datetime import datetime
from flask.cli import with_appcontext
from flask import current_app
import gspread

from .models import db_proxy, UpdateMetadata, Reg_Data, CR_Payments
from .utils import update_timestamp


def register_ops_commands(app):
    """Register operational CLI commands."""

    @app.cli.command("ingest-data")
    @with_appcontext
    def ingest_data():
        """Fetches new records from Google Sheets and saves them to the database."""

        print("[OPS] Running Data Ingestion Task")

        # Get Config and Decode Credentials
        reg_sheet_key = current_app.config.get("REG_SHEET_KEY")
        cr_pay_sheet_key = current_app.config.get("CR_PAY_SHEET_KEY")
        gcp_sa_key_b64 = current_app.config.get("GCP_SA_KEY_B64")
        amount_shirt = current_app.config.get("AMOUNT_SHIRT")
        amount_noshirt = current_app.config.get("AMOUNT_NOSHIRT")

        if not all([reg_sheet_key, cr_pay_sheet_key, gcp_sa_key_b64]):
            print("❌ FATAL: Google Sheets environment variables are not fully set.")
            return

        try:
            decoded_key = base64.b64decode(gcp_sa_key_b64).decode("utf-8")
            credentials = json.loads(decoded_key)
        except Exception as e:
            print(f"❌ FATAL: Could not decode GCP service account key. Error: {e}")
            return

        # Authenticate and Fetch
        try:
            gc = gspread.service_account_from_dict(credentials)

            # Fetch Registration Data
            reg_sheet = gc.open_by_key(reg_sheet_key)
            reg_records = reg_sheet.sheet1.get_all_records()
            print(f"Fetched {len(reg_records)} registrations from Google Sheets.")

            # Fetch CR Payment Data
            cr_pay_sheet = gc.open_by_key(cr_pay_sheet_key)
            cr_pay_records = cr_pay_sheet.sheet1.get_all_records()
            print(f"Fetched {len(cr_pay_records)} CR payments from Google Sheets.")

        except Exception as e:
            print(f"❌ ERROR: Failed to fetch data from Google Sheets: {e}")
            return

        # Process and Insert
        new_records_added = False

        try:
            with db_proxy.atomic():
                # Get existing IDs for efficient checking
                existing_reg_ids = {
                    rec.SubID for rec in Reg_Data.select(Reg_Data.SubID)
                }
                existing_cr_pay_ids = {
                    rec.SubID for rec in CR_Payments.select(CR_Payments.SubID)
                }

                # Process Registrations
                for record in reg_records:
                    if record.get("Submission ID") not in existing_reg_ids:
                        tshirt_interest = record.get("TShirtInterest") == "Yes"
                        payable = amount_shirt if tshirt_interest else amount_noshirt

                        Reg_Data.create(
                            SubID=record["Submission ID"],
                            SubAt=record["Submitted at"],
                            Name=record["Name"],
                            Phone=record["Phone"],
                            Stream=record["Please select your stream and year."],
                            FoodPref=record["FoodPref"],
                            TShirtInt=tshirt_interest,
                            TShirtSize=record.get("TShirtSize") or None,
                            PaymentMethod=(
                                "CR" if "CR" in record["PaymentMethod"] else "Online"
                            ),
                            PaymentScreenshot=record.get("PaymentScreenshot") or None,
                            Payable=payable,
                        )
                        new_records_added = True
                        print(f"  -> New Registration: {record['Name']}")

                # Process CR Payments
                for record in cr_pay_records:
                    if record.get("Submission ID") not in existing_cr_pay_ids:
                        CR_Payments.create(
                            SubID=record["Submission ID"],
                            SubAt=record["Submitted at"],
                            CRID=record["CR-ID"],
                            Name=record["Name"],
                            Phone=record["Phone"],
                            Amount=record["Amount"],
                        )
                        new_records_added = True
                        print(
                            f"  -> New CR Payment: {record['Name']} (Rs. {record['Amount']})"
                        )

        except Exception as e:
            print(f"❌ An error occurred during database insertion: {e}")
            return

        if new_records_added:
            print("✅ New data ingested. Timestamp updated.")
        else:
            print("No new data found.")

        print("[OPS] Data Ingestion Task Finished")

    @app.cli.command("trigger-rebuild")
    @with_appcontext
    def trigger_rebuild():
        """Checks for recent modifications and triggers a GitHub Actions rebuild."""

        print("[OPS] Checking for updates to trigger rebuild ")

        # Use get_or_none in case the table is empty
        metadata = UpdateMetadata.get_or_none(id=1)

        # During first run, if there's no value of LastUpdated, then short circuit and trigger a deploy
        if metadata and (
            not metadata.LastUpdated or metadata.LastModified > metadata.LastUpdated
        ):
            print("Changes detected. Triggering rebuild workflow...")

            owner = current_app.config.get("GH_OWNER")
            repo = current_app.config.get("GH_REPO")
            pat = current_app.config.get("GH_PAT")

            if not all([owner, repo, pat]):
                print("❌ FATAL: GitHub environment variables are not set.")
                return

            try:
                api_url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
                headers = {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {pat}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                payload = {"event_type": "update-profiles"}

                response = requests.post(
                    api_url, json=payload, headers=headers, timeout=10
                )
                response.raise_for_status()

                metadata.LastUpdated = datetime.now()
                metadata.save()
                print("✅ Rebuild triggered successfully and timestamp updated.")

            except requests.RequestException as e:
                print(f"❌ ERROR: Failed to trigger GitHub Action: {e}")
        else:
            print("No new changes detected. Nothing to do.")

        print("[OPS] Trigger Check Finished")
