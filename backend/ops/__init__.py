"""
Operations package for CLI commands.

This package contains all operational CLI commands:
- Data ingestion from Tally API (registration and CR payments)
- GitHub Actions trigger rebuild
"""

from .registration import register_registration_command
from .cr_payments import register_cr_command
from .trigger_rebuild import register_trigger_rebuild_command


def register_ops_commands(app):
    """
    Register all operational CLI commands with the Flask app.

    Commands registered:
    - ingest-api-data: Ingest registration data from Tally API
    - ingest-cr-data: Ingest CR payment data from Tally API
    - trigger-rebuild: Trigger GitHub Actions rebuild
    """

    register_registration_command(app)
    register_cr_command(app)
    register_trigger_rebuild_command(app)
