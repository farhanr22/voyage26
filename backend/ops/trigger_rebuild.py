"""
GitHub Actions trigger rebuild command.
"""

import requests
from datetime import datetime
from flask.cli import with_appcontext
from flask import current_app

from ..models import UpdateMetadata


def register_trigger_rebuild_command(app):
    """Register the trigger-rebuild CLI command."""

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
