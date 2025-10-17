from flask import Blueprint, jsonify, request, current_app
from ..models import Reg_Data, ItemsTaken

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/student-data", methods=["POST"])
def get_student_data():
    """
    API endpoint that returns all verified student data
    for the static site generator.
    """

    data = request.get_json()

    # Check for the API password
    if not data or data.get("password") != current_app.config.get("API_PASSWORD"):
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch all verified profiles from the database
    profiles = list(Reg_Data.select().where(Reg_Data.StudentID.is_null(False)).dicts())

    # Fetch all dispatched items
    # Create a dictionary lookup for items: { 'STUDENTID': ['T-SHIRT', 'TIFFIN'], ... }
    items_by_student = {}
    items_query = ItemsTaken.select(ItemsTaken.StudentID, ItemsTaken.Item).tuples()

    for student_id, item in items_query:
        if student_id not in items_by_student:
            items_by_student[student_id] = []
        items_by_student[student_id].append(item)

    # Process the data into the final format
    students_list = []

    for p in profiles:
        student_id = p.get("StudentID")
        items_received = items_by_student.get(student_id, [])

        students_list.append(
            {
                "id": student_id,
                "name": p.get("Name"),
                "batch": p.get("Stream"),
                "food": p.get("FoodPref"),
                "tshirt": (
                    "Opted out"
                    if not p.get("TShirtSize")
                    else f"Size : {p.get('TShirtSize')}"
                ),
                "paid": int(p.get("Paid") or 0),
                "payable": int(p.get("Payable") or 0),
                "items_rec": ", ".join(items_received) if items_received else "None",
            }
        )

    return jsonify({"data": students_list})


# === NOTIFICATION WORKER ENDPOINTS ==

@api_bp.route('/notifications/next', methods=['POST'])
def get_next_notification():
    """
    Finds the next pending notification and returns its data.
    """

    data = request.get_json()
    
    # Check API password
    if not data or data.get("password") != current_app.config.get("API_PASSWORD"):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Query for one pending notification
    pending_profile = (
        Reg_Data.select(Reg_Data.Name, Reg_Data.Phone, Reg_Data.StudentID)
        .where(
            (Reg_Data.Status == "Verified") &
            (Reg_Data.NotificationStatus == "Pending")
        )
        .first()
    )
    
    # Get the total count of all pending notifications
    pending_count = Reg_Data.select().where(
        (Reg_Data.Status == "Verified") &
        (Reg_Data.NotificationStatus == "Pending")
    ).count()

    # Prepare the response
    if pending_profile:
        # If a profile was found, return its data
        profile_data = {
            "name": pending_profile.Name,
            "phone": pending_profile.Phone,
            "student_id": pending_profile.StudentID
        }
        return jsonify({
            "pending_count": pending_count,
            "data": profile_data
        })
    else:
        # else return an empty data object
        return jsonify({
            "pending_count": 0,
            "data": None
        })

@api_bp.route('/notifications/confirm', methods=['POST'])
def confirm_notification_sent():
    """
    Confirms that a notification has been sent and updates the student's status.
    """

    data = request.get_json()
    
    # Check API password
    if not data or data.get("password") != current_app.config.get("API_PASSWORD"):
        return jsonify({"error": "Unauthorized"}), 401
    
    student_id = data.get("student_id")
    if not student_id:
        return jsonify({"error": "student_id is required"}), 400

    # Find the student and update their status
    try:
        profile_to_update = Reg_Data.get(Reg_Data.StudentID == student_id)
        
        if profile_to_update.NotificationStatus == "Pending":
            profile_to_update.NotificationStatus = "Done"
            profile_to_update.save()
            
            return jsonify({
                "status": "success",
                "message": f"Notification for {student_id} confirmed."
            })
        else:
            return jsonify({
                "status": "noop", # "No Operation"
                "message": f"Notification for {student_id} was already marked as Done."
            })

    except Reg_Data.DoesNotExist:
        return jsonify({"error": f"Student with ID {student_id} not found."}), 404
