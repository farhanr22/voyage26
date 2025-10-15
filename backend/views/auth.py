from flask import Blueprint, render_template, request, flash, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

from ..models import Admins
from ..extensions import hcaptcha, limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    """A standard login form with username, password, and CSRF protection."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class ChangePasswordForm(FlaskForm):
    """Form for changing password."""

    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=5, message="Password must be at least 5 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Change Password")

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("6 per minute", methods=['POST'])
def login():
    form = LoginForm()

    # Captcha validation done separately from WTForms
    if request.method == 'POST':
        if not hcaptcha.verify():
            flash('CAPTCHA verification failed. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        try:
            admin = Admins.get(Admins.username == username)

            # Check if the user exists and the password is correct
            if admin and check_password_hash(admin.passhash, password):

                # Log the user in using Flask-Login
                login_user(admin)

                # Store the session version in the cookie, to be checked on every request
                session["_session_version"] = admin.session_version

                flash("Logged in successfully!", "success")

                return redirect(url_for("main.dashboard"))
            else:
                flash(
                    "Login failed. Please check your username and password.", "danger"
                )
        except Admins.DoesNotExist:
            flash("Login failed. Please check your username and password.", "danger")

    # For a GET request, or if the form is invalid, render the login template
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    form = ChangePasswordForm()

    if form.validate_on_submit():

        # Check if the current password is correct
        if not check_password_hash(current_user.passhash, form.current_password.data):
            flash("Your current password is incorrect. Please try again.", "danger")
        else:
            # Hash the new password
            new_passhash = generate_password_hash(form.new_password.data)

            # Update the user object in the database
            current_user.passhash = new_passhash
            current_user.session_version += 1  # Invalidate old sessions
            current_user.save()

            # Update the session cookie with the new version
            session["_session_version"] = current_user.session_version

            flash("Your password has been changed successfully!", "success")
            return redirect(url_for("main.dashboard"))

    #  Handle validation failures with flash messages
    elif request.method == "POST":
        for field, errors in form.errors.items():
            for error in errors:
                field_label = getattr(form, field).label.text
                flash(f"Error in {field_label}: {error}", "danger")

    return render_template("auth/change_password.html", form=form)
