from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Renders the main dashboard page for authenticated users.
    """
    return render_template('dashboard.html')