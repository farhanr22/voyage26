import peewee as pw
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField
from wtforms.validators import DataRequired

from ..models import Reg_Data, CR_Payments, CR_Profiles
from ..utils import update_timestamp


# === Forms used in this blueprint ===


class VerifyInstallmentForm(FlaskForm):
    """
    A form to securely process installment verifications.
    Uses hidden fields to pass necessary IDs.
    """

    reg_data_subid = HiddenField("Registration ID", validators=[DataRequired()])
    cr_payments_id = HiddenField("CR Payment ID", validators=[DataRequired()])
    submit = SubmitField("Verify Installment")


# === Blueprint ===
cr_payments_bp = Blueprint("cr_payments", __name__, url_prefix="/cr-payments")


# === Routes ===


@cr_payments_bp.route("/")
@login_required
def dashboard():
    """Displays statistics and pending actions for CR Payments."""

    # Query for total payments collected by each CR
    pay_by_cr = list(
        CR_Profiles.select(
            CR_Profiles.Name,
            CR_Profiles.Phone,
            CR_Profiles.Batch,
            pw.fn.COUNT(pw.fn.DISTINCT(CR_Payments.Phone)).alias("UniquePayments"),
            pw.fn.SUM(CR_Payments.Amount).alias("TotalCollected"),
        )
        .join(
            CR_Payments, pw.JOIN.LEFT_OUTER, on=(CR_Profiles.CRID == CR_Payments.CRID)
        )
        .group_by(
            CR_Profiles.CRID, CR_Profiles.Name, CR_Profiles.Phone, CR_Profiles.Batch
        )
        .order_by(
            pw.fn.COUNT(pw.fn.DISTINCT(CR_Payments.Phone)).desc(), CR_Profiles.Batch
        )
        .dicts()
    )

    # Query for payments that have already been matched to a registration
    matched = list(
        CR_Payments.select(
            # Explicitly select the columns you need for the template
            CR_Payments.Name,
            CR_Payments.Amount,
            CR_Payments.MatchedBy,
            CR_Profiles.Batch,  # And the batch from the joined table
        )
        .join(CR_Profiles, on=(CR_Payments.CRID == CR_Profiles.CRID))
        .where(CR_Payments.Status == "Matched")
        .order_by(CR_Profiles.Batch)
        .dicts()
    )

    installments = list(
        Reg_Data.select(
            Reg_Data,
            Reg_Data.SubID.alias("RegDataSubID"),
            Reg_Data.Name.alias("RegDataName"),
            Reg_Data.Stream.alias("RegDataStream"),
            CR_Payments.SubID.alias("CRPaymentsID"),
            CR_Payments.Amount.alias("CRPaymentsAmount"),
            CR_Payments.Name.alias("CRPaymentsName"),
            CR_Profiles.Name.alias("CRProfileName"),
            # Add the one new piece of information we need
            CR_Profiles.Batch.alias("CRProfileBatch"),
        )
        .join(CR_Payments, on=(Reg_Data.Phone == CR_Payments.Phone))
        .join(CR_Profiles, on=(CR_Payments.CRID == CR_Profiles.CRID))
        .where((Reg_Data.Status == "Verified") & (CR_Payments.Status == "Pending"))
        .dicts()
    )

    # Query for payments made by students who haven't registered online yet
    pending_reg = list(
        CR_Payments.select(
            CR_Payments.Name.alias("CRPaymentsName"),
            CR_Payments.Amount.alias("CRPaymentsAmount"),
            CR_Profiles.Name.alias("CRProfileName"),
            CR_Profiles.Batch.alias("CRProfileBatch"),
        )
        .join(CR_Profiles, on=(CR_Payments.CRID == CR_Profiles.CRID))
        .where(
            (CR_Payments.Status == "Pending")
            &
            (~CR_Payments.Phone.in_(Reg_Data.select(Reg_Data.Phone)))
        )
        .order_by(CR_Profiles.Batch)
        .dicts()
    )

    verify_form = VerifyInstallmentForm()

    return render_template(
        "cr_payments/dashboard.html",
        paybycr=pay_by_cr,
        matched=matched,
        installments=installments,
        pending_reg=pending_reg,
        verify_form=verify_form,
    )


@cr_payments_bp.route("/verify-installment", methods=["POST"])
@login_required
def verify_installment():
    """Processes the verification of a second installment payment."""

    form = VerifyInstallmentForm()
    
    if form.validate_on_submit():
        reg_id = form.reg_data_subid.data
        payment_id = form.cr_payments_id.data

        # Find the matching registration and payment record in one query
        match = (
            Reg_Data.select(
                Reg_Data.Paid.alias("RegDataPaid"),
                Reg_Data.Name.alias("RegDataName"),
                CR_Payments.Amount.alias("CRPaid"),
            )
            .join(CR_Payments, on=(Reg_Data.Phone == CR_Payments.Phone))
            .where(
                (Reg_Data.Status == "Verified")
                & (CR_Payments.Status == "Pending")
                & (Reg_Data.SubID == reg_id)
                & (CR_Payments.SubID == payment_id)
            )
            .dicts()
            .first()
        )

        if not match:
            flash("Invalid request. The installment could not be matched.", "danger")
            return redirect(url_for("cr_payments.dashboard"))

        # Perform the database updates
        reg_data_profile = Reg_Data.get(Reg_Data.SubID == reg_id)
        new_amount = int(reg_data_profile.Paid) + int(match["CRPaid"])
        reg_data_profile.Paid = new_amount
        reg_data_profile.save()

        cr_payment_record = CR_Payments.get(CR_Payments.SubID == payment_id)
        cr_payment_record.Status = "Matched"
        cr_payment_record.MatchedBy = current_user.username
        cr_payment_record.save()

        update_timestamp()
        flash(
            f"Updated payment for {match['RegDataName']} to Rs. {new_amount}.",
            "success",
        )
    else:
        flash("An error occurred. Please try again.", "danger")

    return redirect(url_for("cr_payments.dashboard"))
