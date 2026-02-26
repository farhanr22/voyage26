"""
Standalone test script for Tally API data ingestion.

Usage:
    python backend/ops/test_tally_api.py [--mode MODE] [--output OUTPUT]

Options:
    --mode MODE         Test mode: 'registration', 'cr', or 'both' (default: both)
    --output OUTPUT     Output mode: 'verbose' or 'summary' (default: summary)
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables from .env
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
load_dotenv(os.path.join(basedir, ".env"))

# Import ops utilities directly from the module file (avoid __init__.py)
import importlib.util
utils_path = Path(__file__).parent / "utils.py"
spec = importlib.util.spec_from_file_location("ops_utils", utils_path)
ops_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops_utils)

fetch_tally_submissions = ops_utils.fetch_tally_submissions
build_question_map = ops_utils.build_question_map
extract_record_from_submission = ops_utils.extract_record_from_submission


# Field mappings (same as ops/registration.py and ops/cr_payments.py)
REGISTRATION_FIELD_MAPPING = {
    "Name": "name",
    "Phone": "phone",
    "Stream": "batch",
    "FoodPref": "food_preference",
    "TShirtSize": "tshirt_size",
    "tshirt_preference": "tshirt_preference",
}

CR_FIELD_MAPPING = {
    "CRID": "cr_id",
    "Name": "name",
    "Phone": "phone",
    "Amount": "amount",
}


def process_registration_record(record, verbose=False):
    """Process and display registration record."""

    if verbose:
        tshirt_interest = record.get("tshirt_preference") == "Yes"
        amount_shirt = int(os.environ.get("AMOUNT_SHIRT", 1200))
        amount_noshirt = int(os.environ.get("AMOUNT_NOSHIRT", 1000))
        payable = amount_shirt if tshirt_interest else amount_noshirt

        print(f"\n[Registration] {record['Name']}")
        print(f"  SubID:             {record['SubID']}")
        print(f"  SubAt:             {record['SubAt']}")
        print(f"  Phone:             {record['Phone']}")
        print(f"  Stream:            {record['Stream']}")
        print(f"  FoodPref:          {record['FoodPref']}")
        print(f"  TShirtInterest:    {tshirt_interest}")
        print(f"  TShirtSize:        {record.get('TShirtSize')}")
        print(f"  PaymentMethod:     CR")
        print(f"  PaymentScreenshot: None")
        print(f"  Payable:           {payable}")
    else:
        print(f"  - {record['Name']} ({record['Phone']})")


def process_cr_record(record, verbose=False):
    """Process and display CR payment record."""

    if verbose:
        print(f"\n[CR Payment] {record['Name']}")
        print(f"  SubID:      {record['SubID']}")
        print(f"  SubAt:      {record['SubAt']}")
        print(f"  CRID:       {record['CRID']}")
        print(f"  Phone:      {record['Phone']}")
        print(f"  Amount:     Rs. {record['Amount']}")
        print(f"  Status:     Pending")
    else:
        print(f"  - {record['Name']} (CRID: {record['CRID']}, Amount: Rs. {record['Amount']})")


def test_registration_form(verbose=False):
    """Test the registration form ingestion."""

    print("\n" + "=" * 60)
    print("[TEST] Registration Form")
    print("=" * 60)

    tally_api_key = os.environ.get("TALLY_API_KEY")
    tally_form_id = os.environ.get("TALLY_REGISTRATION_FORM_ID")

    if not tally_api_key or not tally_form_id:
        print("[ERROR] Registration form credentials not set.")
        print("  TALLY_API_KEY or TALLY_REGISTRATION_FORM_ID is missing.")
        return None

    try:
        api_response = fetch_tally_submissions(tally_api_key, tally_form_id)

        questions = api_response.get("questions", [])
        submissions = api_response.get("submissions", [])

        required_keys = list(REGISTRATION_FIELD_MAPPING.values())
        question_map = build_question_map(questions, required_keys)

        if verbose:
            print(f"Question Map: {question_map}")
        print(f"Total submissions: {len(submissions)}")

        if not verbose:
            print("\nRecent submissions:")

        for submission in submissions:
            record = extract_record_from_submission(
                submission, question_map, REGISTRATION_FIELD_MAPPING
            )
            process_registration_record(record, verbose)

        if not verbose:
            print(f"\n[Summary] {len(submissions)} total registration submissions")

        return len(submissions)

    except Exception as e:
        print(f"[ERROR] Failed to fetch registration data: {e}")
        return None


def test_cr_form(verbose=False):
    """Test the CR form ingestion."""

    print("\n" + "=" * 60)
    print("[TEST] CR Form")
    print("=" * 60)

    tally_api_key = os.environ.get("TALLY_API_KEY")
    tally_form_id = os.environ.get("TALLY_CR_FORM_ID")

    if not tally_api_key or not tally_form_id:
        print("[ERROR] CR form credentials not set.")
        print("  TALLY_API_KEY or TALLY_CR_FORM_ID is missing.")
        return None

    try:
        api_response = fetch_tally_submissions(tally_api_key, tally_form_id)

        questions = api_response.get("questions", [])
        submissions = api_response.get("submissions", [])

        required_keys = list(CR_FIELD_MAPPING.values())
        question_map = build_question_map(questions, required_keys)

        if verbose:
            print(f"Question Map: {question_map}")
        print(f"Total submissions: {len(submissions)}")

        if not verbose:
            print("\nRecent submissions:")

        for submission in submissions:
            record = extract_record_from_submission(
                submission, question_map, CR_FIELD_MAPPING
            )
            process_cr_record(record, verbose)

        if not verbose:
            print(f"\n[Summary] {len(submissions)} total CR submissions")

        return len(submissions)

    except Exception as e:
        print(f"[ERROR] Failed to fetch CR data: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Test Tally API data ingestion"
    )
    parser.add_argument(
        "--mode",
        choices=["registration", "cr", "both"],
        default="both",
        help="Test mode: 'registration', 'cr', or 'both' (default: both)"
    )
    parser.add_argument(
        "--output",
        choices=["verbose", "summary"],
        default="summary",
        help="Output mode: 'verbose' shows all details, 'summary' shows counts (default: summary)"
    )

    args = parser.parse_args()

    verbose = args.output == "verbose"
    mode = args.mode

    print(f"[TEST] Starting Tally API Tests (Mode: {mode}, Output: {args.output})")

    reg_count = 0
    cr_count = 0
    has_error = False

    if mode == "registration":
        reg_count = test_registration_form(verbose)
        if reg_count is None:
            has_error = True
            reg_count = 0
    elif mode == "cr":
        cr_count = test_cr_form(verbose)
        if cr_count is None:
            has_error = True
            cr_count = 0
    elif mode == "both":
        reg_count = test_registration_form(verbose)
        cr_count = test_cr_form(verbose)
        if reg_count is None:
            has_error = True
            reg_count = 0
        if cr_count is None:
            has_error = True
            cr_count = 0

    print("\n" + "=" * 60)
    print("[TEST] Summary")
    print("=" * 60)
    if mode in ["registration", "both"]:
        print(f"  Registration submissions: {reg_count}")
    if mode in ["cr", "both"]:
        print(f"  CR submissions:           {cr_count}")

    print("\n[TEST] All tests finished!")

    if has_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
