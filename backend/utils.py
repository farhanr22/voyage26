import random
import string
from datetime import datetime

from flask import current_app

from .models import UpdateMetadata, Reg_Data


def generate_unique_id() -> str:
    """
    Generates a unique 4-character alphanumeric StudentID by querying
    the database directly to check for collisions.

    Returns:
        A unique 4-character string that is not present in the Reg_Data table.
    """

    # Fetch all existing StudentIDs from the database into a set
    existing_ids = {
        sid
        for (sid,) in Reg_Data.select(Reg_Data.StudentID)
        .where(Reg_Data.StudentID.is_null(False))
        .tuples()
    }

    while True:
        # Generate a new candidate ID.
        new_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

        # If the new ID is not in our set of existing IDs, it's unique, return it   
        if new_id not in existing_ids:
            return new_id


def update_timestamp():
    """
    Updates the 'LastModified' timestamp in the UpdateMetadata table.
    """

    try:
        metadata, created = UpdateMetadata.get_or_create(id=1)
        metadata.LastModified = datetime.now()
        metadata.save()
    except Exception as e:
        current_app.logger.warning(f"Error updating timestamp : '{e}'.")


def get_current_timestamp_str() -> str:
    """
    Returns the current time in the app's configured timezone
    as a standardized ISO-like string.
    Format: YYYY-MM-DDTHH:MM:SS
    """
    tz = current_app.config.get("TIMEZONE")
    dt_now = datetime.now(tz)
    return dt_now.strftime("%Y-%m-%dT%H:%M:%S")
