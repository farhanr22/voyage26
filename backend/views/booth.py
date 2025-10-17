# backend/views/booth.py

import peewee as pw
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from ..models import Booth_Operators, ItemsTaken, Reg_Data
from ..utils import get_current_timestamp_str, update_timestamp

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


# === Operator-Facing Routes ===


@booth_bp.route("/<string:item>")
def operator_page(item):
    """Renders the standalone page for booth operators."""

    # Convert to uppercase to match the config
    booth_item = item.upper()
    if booth_item not in current_app.config.get("BOOTHS", []):
        # You should create a simple 'booth_not_found.html' template
        return render_template("booth/not_found.html", item=item), 404

    return render_template("booth/booth_page.html", booth_item=booth_item)


@booth_bp.route("/check-username", methods=["POST"])
def check_username():
    """API endpoint to validate a booth operator's username."""

    data = request.get_json()
    username = data.get("username")

    # Check if a valid, non-removed operator exists with this username
    is_valid = (
        Booth_Operators.select()
        .where(
            (Booth_Operators.Username == username)
            & (Booth_Operators.RemovedBy.is_null(True))
        )
        .exists()
    )

    return jsonify(valid=is_valid)


@booth_bp.route("/check-reg", methods=["POST"])
def check_registration():
    """
    API endpoint to fetch a student's registration details.
    Returns a JSON response containing a rendered HTML fragment.
    """

    data = request.get_json()
    username = data.get("username")
    student_id = data.get("id", "").upper()
    item = data.get("item")

    # First, validate the operator
    is_operator_valid = (
        Booth_Operators.select()
        .where(
            (Booth_Operators.Username == username)
            & (Booth_Operators.RemovedBy.is_null(True))
        )
        .exists()
    )

    if not is_operator_valid:
        return jsonify(
            authorized=False,
            fragment="<p class='text-danger'>Operator ID not recognized.</p>",
        )

    # Fetch the student profile
    profile = Reg_Data.select().where(Reg_Data.StudentID == student_id).dicts().first()

    if not profile:
        return jsonify(
            authorized=True,
            fragment="<p class='alert alert-warning'>Could not find a profile with that Student ID.</p>",
        )

    # Check if this specific item has already been taken
    previously_taken_items = list(
        ItemsTaken.select().where(ItemsTaken.StudentID == student_id).dicts()
    )

    already_taken_this_item = any(x["Item"] == item for x in previously_taken_items)

    # Render the HTML fragment using the fetched data
    fragment = render_template(
        "booth/profile_fragment.html",
        profile=profile,
        prev_items=previously_taken_items,
        already_taken=already_taken_this_item,
        booth_item=item,  # Pass the current booth item to the fragment
    )

    return jsonify(authorized=True, fragment=fragment)


@booth_bp.route("/dispatch", methods=["POST"])
def dispatch_item():
    """API endpoint to record the dispatch of an item."""
    
    data = request.get_json()
    username = data.get("username")
    student_id = data.get("id", "").upper()
    item = data.get("item")

    # Validate the booth item itself
    if item not in current_app.config.get("BOOTHS", []):
        return jsonify(authorized=True, success=False, message="Unrecognized Item.")

    # Validate the operator
    if (
        not Booth_Operators.select()
        .where(
            (Booth_Operators.Username == username)
            & (Booth_Operators.RemovedBy.is_null(True))
        )
        .exists()
    ):
        return jsonify(
            authorized=False, success=False, message="Unrecognized Booth Operator."
        )

    # Check if the student exists
    if not Reg_Data.select().where(Reg_Data.StudentID == student_id).exists():
        return jsonify(authorized=True, success=False, message="Profile doesn't exist.")

    # Check if this exact item has already been given to this student
    if (
        ItemsTaken.select()
        .where((ItemsTaken.StudentID == student_id) & (ItemsTaken.Item == item))
        .exists()
    ):
        return jsonify(
            authorized=True,
            success=False,
            message="This item has already been dispatched to this student.",
        )

    # All checks passed, create the record
    try:
        ItemsTaken.create(
            StudentID=student_id,
            GivenBy=username,
            Item=item,
            TakenAt=get_current_timestamp_str(),  # Use our new timestamp function
        )
        
        update_timestamp() # To update student profile page

        return jsonify(
            authorized=True,
            success=True,
            message=f"Item '{item}' successfully dispatched!",
        )
    except Exception as e:
        print(f"--- DISPATCH ERROR ---: {e}")
        return jsonify(
            authorized=True, success=False, message="A database error occurred."
        )
