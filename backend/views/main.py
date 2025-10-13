from flask import Blueprint, render_template
from flask_login import login_required
from collections import defaultdict
import peewee as pw
from ..models import Reg_Data, CR_Payments

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Gathers all application statistics and renders the main dashboard."""

    # Initialize dict
    data = {
        "reg_status": {"verified": 0, "pending": 0, "rejected": 0, "total": 0},
        "shirt_sizes": {
            "XS": {"verified": 0, "overall": 0},
            "S": {"verified": 0, "overall": 0},
            "M": {"verified": 0, "overall": 0},
            "L": {"verified": 0, "overall": 0},
            "XL": {"verified": 0, "overall": 0},
        },
        "t_shirt_total": {"verified": 0, "overall": 0},
        "food_pref": {"veg": 0, "non_veg": 0},
        "finances": {
            "total_payable": 0,
            "verified_collection": 0,
            "online_verified": 0,
            "cr_collection": 0,
        },
        "notification_status": {"sent": 0, "pending": 0},
    }
    stream_data = defaultdict(lambda: {"overall": 0, "verified": 0})

    # Fetch registrations data
    all_regs = list(Reg_Data.select().dicts())

    # Calculate stats
    for reg in all_regs:
        is_verified = reg.get("Status") == "Verified"

        # Reg Status & Stream Data
        data["reg_status"]["total"] += 1
        stream = reg.get("Stream")
        if stream:
            stream_data[stream]["overall"] += 1

        if is_verified:
            data["reg_status"]["verified"] += 1
            if stream:
                stream_data[stream]["verified"] += 1
        elif reg.get("Status") == "Pending":
            data["reg_status"]["pending"] += 1
        else:
            data["reg_status"]["rejected"] += 1

        # Finances
        payable = reg.get("Payable", 0)
        paid = reg.get("Paid") or 0
        data["finances"]["total_payable"] += payable
        if is_verified:
            # We'll only count verified online payments here, 
            # total including cr payments is calculated later
            data["finances"]["verified_collection"] += paid
            if reg.get("PaymentMethod") == "Online":
                data["finances"]["online_verified"] += paid

        # T-Shirt & Food Data
        shirt_size = reg.get("TShirtSize")
        if shirt_size and shirt_size in data["shirt_sizes"]:
            data["shirt_sizes"][shirt_size]["overall"] += 1
            data["t_shirt_total"]["overall"] += 1
            if is_verified:
                data["shirt_sizes"][shirt_size]["verified"] += 1
                data["t_shirt_total"]["verified"] += 1

        notification = reg.get("NotificationStatus", None)
        if notification:
            if notification == "Pending":
                data["notification_status"]["pending"] += 1
            else: # status is "Done"
                data["notification_status"]["sent"] += 1

        if reg.get("FoodPref") == "Veg":
            data["food_pref"]["veg"] += 1
        else:
            data["food_pref"]["non_veg"] += 1

    # All CR collctions, regardless of verification status
    cr_payments_total = CR_Payments.select(pw.fn.SUM(CR_Payments.Amount)).scalar() or 0
    data["finances"]["cr_collection"] = cr_payments_total

    # Pre-calculation for Template
    if data["finances"]["total_payable"] > 0:
        data["finances"]["collected_percent"] = round(
            (data["finances"]["verified_collection"] / data["finances"]["total_payable"])
            * 100
        )
    else:
        data["finances"]["collected_percent"] = 0

    return render_template(
        "main/dashboard.html", data=data, stream_reg=dict(stream_data)
    )
