import getpass
from werkzeug.security import generate_password_hash
from flask.cli import with_appcontext
import click
from .config import Config

from .models import (
    db_proxy,
    Admins,
    Reg_Data,
    CR_Payments,
    CR_Profiles,
    Booth_Operators,
    ItemsTaken,
    UpdateMetadata,
)
import random


def register_commands(app):
    """Register command line commands with the Flask app."""

    @app.cli.command("init-db")
    def init_db():
        """
        Initializes the database by creating all tables.
        Uses safe=True to avoid overwriting existing tables.
        """

        models_to_create = [
            Admins,
            Reg_Data,
            CR_Payments,
            CR_Profiles,
            Booth_Operators,
            ItemsTaken,
            UpdateMetadata,
        ]
        with db_proxy:
            db_proxy.create_tables(models_to_create, safe=True)
        print("✅ Database tables created successfully (if they didn't exist).")

    @app.cli.command("drop-db")
    def drop_db():
        """Drops all database tables. USE WITH CAUTION."""

        confirm = (
            input("This will delete all data. Are you sure? (y/N): ").strip().lower()
        )
        if confirm == "y":
            models_to_drop = [
                UpdateMetadata,
                ItemsTaken,
                Booth_Operators,
                CR_Profiles,
                CR_Payments,
                Reg_Data,
                Admins,
            ]
            with db_proxy:
                db_proxy.drop_tables(models_to_drop)
            print("💥 All database tables dropped.")
        else:
            print("Operation cancelled.")

    @app.cli.command("add-admin")
    def add_admin():
        """Adds a new admin user to the database."""
        username = input("Enter username: ").strip()

        # Check if user already exists
        if Admins.select().where(Admins.username == username).exists():
            print(f"❌ Error: User '{username}' already exists.")
            return

        password = getpass.getpass("Enter password: ").strip()
        pass_confirm = getpass.getpass("Confirm password: ").strip()

        if password != pass_confirm:
            print("❌ Error: Passwords do not match.")
            return

        hashed_password = generate_password_hash(password)

        try:
            with db_proxy.atomic() as transaction:
                Admins.create(username=username, passhash=hashed_password)
            print(f"✅ Admin user '{username}' created successfully.")
        except Exception as e:
            print(f"❌ Error creating user: {e}")

    @app.cli.command("change-password")
    def change_password():
        """Changes an existing admin user's password."""
        username = input("Enter username of the admin to modify: ").strip()

        try:
            admin_to_update = Admins.get(Admins.username == username)
        except Admins.DoesNotExist:
            print(f"❌ Error: User '{username}' not found.")
            return

        print(f"Changing password for user: {admin_to_update.username}")
        password = getpass.getpass("Enter new password: ").strip()
        pass_confirm = getpass.getpass("Confirm new password: ").strip()

        if password != pass_confirm:
            print("❌ Error: Passwords do not match.")
            return

        hashed_password = generate_password_hash(password)

        try:
            with db_proxy.atomic() as transaction:
                # Increment the session_version to log out other sessions
                admin_to_update.passhash = hashed_password
                admin_to_update.session_version += 1
                admin_to_update.save()
            print(f"✅ Password for '{username}' updated successfully.")
            print(
                f"   Session version incremented to {admin_to_update.session_version}."
            )
        except Exception as e:
            print(f"❌ Error updating password: {e}")

    @app.cli.command("seed-data")
    @with_appcontext
    def seed_data():
        """
        Wipes and seeds the database with a complete and varied set of dummy data,
        including edge cases.
        """

        # CONFIGURATION
        TOTAL_PROFILES = 60
        PROFILES_PENDING_ONLINE_REG = 5
        PROFILES_UNVERIFIABLE = 5

        FIRST_NAMES = [
            "Paper",
            "Cloud",
            "Table",
            "Echo",
            "River",
            "Pixel",
            "Stone",
            "Light",
            "Drum",
            "Shadow",
        ]

        LAST_NAMES = [
            "Forest",
            "Glass",
            "Engine",
            "Bridge",
            "Cable",
            "Orbit",
            "Signal",
            "Thread",
            "Dust",
            "Beacon",
        ]

        BATCH_WEIGHTS = {
            "B.Tech 1st": 30,
            "B.Tech 2nd": 30,
            "B.Tech 3rd": 30,
            "MCA 1st": 20,
            "MCA 2nd": 20,
            "MCS 1st": 10,
            "MCS 2nd": 10,
        }
        TSHIRT_INTEREST_WEIGHTS = {"Yes": 70, "No": 30}
        TSHIRT_SIZES = ["S", "M", "L", "XL"]
        FOOD_PREF_WEIGHTS = {"Non Veg": 80, "Veg": 20}
        PAYMENT_METHOD_WEIGHTS = {"CR": 80, "Online": 20}
        PAYMENT_AMOUNT_WEIGHTS = {"Full": 70, "Partial": 30}
        PARTIAL_AMOUNT = 500
        # ---

        # WIPE EXISTING DATA SAFELY
        if click.confirm(
            "This will DELETE ALL existing registrations, payments, and CR profiles. Do you want to continue?",
            abort=True,
        ):
            print("Wiping existing data...")
            with db_proxy.atomic():
                CR_Payments.delete().execute()
                Reg_Data.delete().execute()
                CR_Profiles.delete().execute()
            print("Data wiped successfully.")

        # GENERATE CR PROFILES
        print(f"Generating one CR for each of the {len(BATCH_WEIGHTS)} batches...")
        dummy_crs = []
        for i, batch_name in enumerate(BATCH_WEIGHTS.keys()):
            dummy_crs.append(
                {
                    "CRID": f"CR{i:02d}",
                    "Name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    "Phone": f"8{random.randint(100000000, 999999999)}",
                    "Batch": batch_name,
                }
            )

        new_regs = []
        new_cr_pays = []

        # GENERATE MAIN CHUNK OF PROFILES 

        print(f"Generating {TOTAL_PROFILES} standard profiles...")

        for i in range(TOTAL_PROFILES):
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            phone = f"9{random.randint(100000000, 999999999)}"
            tshirt_interest = random.choices(
                list(TSHIRT_INTEREST_WEIGHTS.keys()),
                weights=list(TSHIRT_INTEREST_WEIGHTS.values()),
                k=1,
            )[0]
            tshirt_size = (
                random.choice(TSHIRT_SIZES) if tshirt_interest == "Yes" else None
            )
            payable = (
                Config.AMOUNT_SHIRT
                if tshirt_interest == "Yes"
                else Config.AMOUNT_NOSHIRT
            )
            payment_method = random.choices(
                list(PAYMENT_METHOD_WEIGHTS.keys()),
                weights=list(PAYMENT_METHOD_WEIGHTS.values()),
                k=1,
            )[0]

            reg_data_dict = {
                "SubID": f"DUMMY{i:03d}",
                "SubAt": "",
                "Name": full_name,
                "Phone": phone,
                "Stream": random.choices(
                    list(BATCH_WEIGHTS.keys()),
                    weights=list(BATCH_WEIGHTS.values()),
                    k=1,
                )[0],
                "FoodPref": random.choices(
                    list(FOOD_PREF_WEIGHTS.keys()),
                    weights=list(FOOD_PREF_WEIGHTS.values()),
                    k=1,
                )[0],
                "TShirtInt": tshirt_interest == "Yes",
                "TShirtSize": tshirt_size,
                "Payable": payable,
                "PaymentMethod": payment_method,
            }

            payment_type = random.choices(
                list(PAYMENT_AMOUNT_WEIGHTS.keys()),
                weights=list(PAYMENT_AMOUNT_WEIGHTS.values()),
                k=1,
            )[0]
            paid_amount = payable if payment_type == "Full" else PARTIAL_AMOUNT

            if payment_method == "Online":
                safe_name = full_name.replace(" ", "+")

                reg_data_dict["PaymentScreenshot"] = (
                    f"https://placehold.co/400x600/white/steelblue/png?text={safe_name}+\\n+Paid+Rs.{paid_amount}+via+UPI"
                )
            else:  # CR payment
                reg_data_dict["PaymentScreenshot"] = None

                new_cr_pays.append(
                    {
                        "SubID": f"CRDUMMY{i:03d}",
                        "SubAt": "",
                        "CRID": random.choice(dummy_crs)["CRID"],
                        "Name": full_name,
                        "Phone": phone,
                        "Amount": paid_amount,
                    }
                )
            new_regs.append(reg_data_dict)

        # Generate "Pending Online Registration" Edge Cases
        print(
            f"Generating {PROFILES_PENDING_ONLINE_REG} profiles for 'Pending Online Registration'..."
        )
        for i in range(PROFILES_PENDING_ONLINE_REG):
            # These are just CR payments with no corresponding Reg_Data entry.
            new_cr_pays.append(
                {
                    "SubID": f"PENDINGREG{i:03d}",
                    "SubAt": "",
                    "CRID": random.choice(dummy_crs)["CRID"],
                    "Name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} (No Reg)",
                    "Phone": f"7{random.randint(100000000, 999999999)}",
                    "Amount": 1100,
                }
            )

        # Generate "Unverifiable" Edge Cases
        print(
            f"Generating {PROFILES_UNVERIFIABLE} profiles for 'Unverifiable Registrations'..."
        )
        for i in range(PROFILES_UNVERIFIABLE):
            # Reg_Data entries with PaymentMethod='CR' but no matching CR_Payment.
            new_regs.append(
                {
                    "SubID": f"UNVERIF{i:03d}",
                    "SubAt": "",
                    "Name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} (Unverifiable)",
                    "Phone": f"6{random.randint(100000000, 999999999)}",
                    "Stream": random.choices(
                        list(BATCH_WEIGHTS.keys()),
                        weights=list(BATCH_WEIGHTS.values()),
                        k=1,
                    )[0],
                    "FoodPref": "Non Veg",
                    "TShirtInt": True,
                    "TShirtSize": "L",
                    "Payable": Config.AMOUNT_SHIRT,
                    "PaymentMethod": "CR",
                    "PaymentScreenshot": None,
                }
            )

        # Insert into Database ---
        try:
            with db_proxy.atomic():
                if dummy_crs:
                    CR_Profiles.insert_many(dummy_crs).execute()
                if new_regs:
                    Reg_Data.insert_many(new_regs).execute()
                if new_cr_pays:
                    CR_Payments.insert_many(new_cr_pays).execute()

            print(
                f"✅ Seeded {len(dummy_crs)} CRs, {len(new_regs)} registrations, and {len(new_cr_pays)} CR payments."
            )
        except Exception as e:
            print(f"❌ An error occurred during database insertion: {e}")
