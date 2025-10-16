# backend/views/registrations.py

import peewee as pw
from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional

from ..models import Reg_Data, CR_Payments, CR_Profiles
from ..utils import generate_unique_id, update_timestamp

# === Forms used in this blueprint ===


class VerificationForm(FlaskForm):
    """Form for verifying or rejecting a registration."""

    amount = IntegerField(
        "Verified Amount", validators=[Optional()]
    )
    verify = SubmitField("Verify")
    reject = SubmitField("Reject")


class UnrejectForm(FlaskForm):
    """A simple form with only a submit button for CSRF protection."""

    submit = SubmitField("Unreject")


# === Blueprint ===
registrations_bp = Blueprint("registrations", __name__, url_prefix="/registrations")


# === Routes ===


@registrations_bp.route("/")
@login_required
def list_all():
    """Displays the main registrations dashboard, sorted into categories."""

    regs = list(Reg_Data.select().order_by(Reg_Data.Stream).dicts())

    cr_pay_phones = {
        c["Phone"]
        for c in CR_Payments.select(CR_Payments.Phone)
        .where(CR_Payments.Status == "Pending")
        .dicts()
    }

    verified = [x for x in regs if x["Status"] == "Verified"]
    rejected = [x for x in regs if x["Status"] == "Rejected"]

    verifiable = [
        x
        for x in regs
        if x["Status"] == "Pending"
        and (
            (x["Phone"] in cr_pay_phones and x["PaymentMethod"] == "CR")
            or (x["PaymentMethod"] == "Online")
        )
    ]
    verifiable.sort(key=lambda x: x["PaymentMethod"] != "Online")

    unverifiable = [
        x
        for x in regs
        if x["PaymentMethod"] == "CR"
        and x["Phone"] not in cr_pay_phones
        and x["Status"] == "Pending"
    ]

    unreject_form = UnrejectForm()

    data = {
        "verified": verified,
        "rejected": rejected,
        "verifiable": verifiable,
        "unverifiable": unverifiable,
    }

    return render_template(
        "registrations/list.html", data=data, unreject_form=unreject_form
    )


@registrations_bp.route("/view/<string:subid>", methods=["GET"])
@login_required
def view_registration(subid):
    """Shows the details for a single, verifiable registration."""

    profile = Reg_Data.select().where(Reg_Data.SubID == subid).dicts().first()
    if not profile:
        flash("There's no entry with that submission ID.", "danger")
        return redirect(url_for("registrations.list_all"))

    matching_pays = list(
        CR_Payments.select(
            CR_Payments,
            CR_Payments.Name.alias("PaidAs"),
            CR_Profiles.Name.alias("CRName"),
            CR_Profiles.Phone.alias("CRPhone"),
        )
        .join(CR_Profiles, on=(pw.fn.TRIM(CR_Payments.CRID) == CR_Profiles.CRID))
        .where(
            (CR_Payments.Phone == profile["Phone"]) & (CR_Payments.Status == "Pending")
        )
        .dicts()
    )

    form = VerificationForm()

    return render_template(
        "registrations/view.html", profile=profile, crpays=matching_pays, form=form
    )


@registrations_bp.route("/process/<string:subid>", methods=["POST"])
@login_required
def process_registration(subid):
    """Handles the verification or rejection of a registration."""

    profile = Reg_Data.get_or_none(Reg_Data.SubID == subid)
    if not profile:
        flash("There's no entry with that submission ID.", "danger")
        return redirect(url_for("registrations.list_all"))

    if profile.Status != "Pending":
        flash("This registration has already been processed.", "warning")
        return redirect(url_for("registrations.list_all"))

    form = VerificationForm()
    if form.validate_on_submit():
        if form.reject.data:
            profile.Status = "Rejected"
            profile.VerifiedBy = current_user.username
            profile.save()
            flash(f"Rejected entry for {profile.Name}.", "success")

        elif form.verify.data:
            paid_amount = form.amount.data
            shirt_amount = current_app.config["AMOUNT_SHIRT"]

            if not paid_amount or paid_amount <= 0 or paid_amount > shirt_amount:
                flash("Paid amount is out of bounds or invalid.", "danger")
                return redirect(url_for("registrations.view_registration", subid=subid))

            # Get a new, unique ID for the verified profile
            new_id = generate_unique_id()

            profile.Status = "Verified"
            profile.VerifiedBy = current_user.username
            profile.Paid = paid_amount
            profile.StudentID = new_id
            profile.NotificationStatus = "Pending"
            profile.save()

            CR_Payments.update(Status="Matched", MatchedBy=current_user.username).where(
                CR_Payments.Phone == profile.Phone
            ).execute()

            update_timestamp()
            flash(f"Verified {profile.Name} with amount: Rs. {paid_amount}", "success")
    else:
        # If form validation fails, flash the errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")

                return redirect(url_for("registrations.view_registration", subid=subid))

    return redirect(url_for("registrations.list_all"))


@registrations_bp.route("/unreject/<string:subid>", methods=["POST"])
@login_required
def unreject(subid):
    """Changes a 'Rejected' registration back to 'Pending'."""

    form = UnrejectForm()
    if form.validate_on_submit():  # This primarily checks for the CSRF token
        profile = Reg_Data.get_or_none(
            (Reg_Data.SubID == subid) & (Reg_Data.Status == "Rejected")
        )
        if not profile:
            flash("Entry doesn't exist or was not rejected.", "danger")
        else:
            profile.Status = "Pending"
            profile.VerifiedBy = None
            profile.save()
            flash(f"Unrejected entry for {profile.Name}.", "success")
    else:
        flash("Invalid request.", "danger")

    return redirect(url_for("registrations.list_all"))


@registrations_bp.route("/all")
@login_required
def view_all_registrations():
    """A simple table view of all registrations, regardless of status."""

    profiles = list(Reg_Data.select().order_by(Reg_Data.Stream).dicts())
    return render_template("registrations/all.html", profiles=profiles)
