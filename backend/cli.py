# backend/cli.py
import getpass
from werkzeug.security import generate_password_hash
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
