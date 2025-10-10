
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from ..models import Admins

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

class LoginForm(FlaskForm):
    """A standard login form with username, password, and CSRF protection."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
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
                session['_session_version'] = admin.session_version
                
                flash('Logged in successfully!', 'success')
                
                return redirect(url_for('main.dashboard'))
            else:
                flash('Login failed. Please check your username and password.', 'danger')
        except Admins.DoesNotExist:
            flash('Login failed. Please check your username and password.', 'danger')
            
    # For a GET request, or if the form is invalid, render the login template
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))