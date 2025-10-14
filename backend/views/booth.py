# backend/views/booth.py

import peewee as pw
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from ..models import Booth_Operators, ItemsTaken, Reg_Data

# === Forms used in this blueprint ===


class AddOperatorForm(FlaskForm):
    """Form for adding a new booth operator."""

    username = StringField(
        "Operator ID", validators=[DataRequired(), Length(min=3, max=20)]
    )
    fullname = StringField(
        "Full Name", validators=[DataRequired(), Length(min=3, max=50)]
    )
    phone = StringField(
        "Phone Number", validators=[DataRequired(), Length(min=10, max=15)]
    )
    submit = SubmitField("Add Operator")


class RemoveOperatorForm(FlaskForm):
    """Form with only a submit button for CSRF protection."""

    submit = SubmitField("Remove")


# === Blueprint ===
booth_bp = Blueprint("booth", __name__, url_prefix="/booth-admin")


# === Routes ===


@booth_bp.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    add_form = AddOperatorForm()
    remove_form = RemoveOperatorForm()

    # POST Request
    if add_form.validate_on_submit():
        username = add_form.username.data
        name = add_form.fullname.data
        phone = add_form.phone.data

        if (
            Booth_Operators.select()
            .where(Booth_Operators.Username == username)
            .exists()
        ):
            flash("Username already exists.", "danger")
        else:
            try:
                Booth_Operators.create(
                    Username=username,
                    Name=name,
                    Phone=phone,
                    AddedBy=current_user.username,
                )
                flash(f"Booth operator '{username}' added successfully!", "success")
            except pw.IntegrityError as e:
                flash("A database error occurred.", "danger")

        return redirect(url_for("booth.dashboard"))

    elif request.method == "POST":
        # If the form failed validation on a POST request, flash the errors.
        for field, errors in add_form.errors.items():
            for error in errors:
                field_label = getattr(add_form, field).label.text
                flash(f"Error in {field_label}: {error}", "danger")

    # GET Request Logic (and fall-through for failed POST)
    operators = list(
        Booth_Operators.select(
            Booth_Operators, pw.fn.COUNT(ItemsTaken.id).alias("items_count")
        )
        .join(
            ItemsTaken,
            pw.JOIN.LEFT_OUTER,
            on=(Booth_Operators.Username == ItemsTaken.GivenBy),
        )
        .group_by(Booth_Operators.id)
        .order_by(Booth_Operators.RemovedBy.is_null(False), Booth_Operators.Username)
        .dicts()
    )

    given_items = list(
        ItemsTaken.select(
            ItemsTaken,
            Reg_Data.Name.alias("StudentName"),
            Reg_Data.Stream,
            Reg_Data.Paid,
            Reg_Data.Payable,
        )
        .join(Reg_Data, on=(ItemsTaken.StudentID == Reg_Data.StudentID))
        .order_by(ItemsTaken.TakenAt.desc())
        .dicts()
    )

    return render_template(
        "booth/dashboard.html",
        operators=operators,
        given_items=given_items,
        add_form=add_form,
        remove_form=remove_form,
    )


@booth_bp.route("/remove/<string:username>", methods=["POST"])
@login_required
def remove_operator(username):
    """Handles the removal of a booth operator."""

    remove_form = RemoveOperatorForm()

    if remove_form.validate_on_submit():
        operator = Booth_Operators.get_or_none(
            (Booth_Operators.Username == username)
            & (Booth_Operators.RemovedBy.is_null(True))
        )
        if operator:
            operator.RemovedBy = current_user.username
            operator.save()
            flash(f"Operator '{username}' has been removed.", "success")
        else:
            flash("Operator not found or already removed.", "warning")
    else:
        flash("Invalid request.", "danger")

    return redirect(url_for("booth.dashboard"))
